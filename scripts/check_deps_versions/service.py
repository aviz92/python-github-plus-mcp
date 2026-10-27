import json
import re
import tomllib
import urllib.request
from pathlib import Path

from custom_python_logger import get_logger

logger = get_logger(__name__)

DEFAULT_PYPROJECT_PATH: Path = Path(__file__).parent.parent.parent / "pyproject.toml"

_NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
_VERSION_RE = re.compile(r"(?:==|!=|<=|>=|~=|<|>)\s*([A-Za-z0-9][A-Za-z0-9.\-_+]*)")


def parse_requirement(requirement: str) -> tuple[str, str | None]:
    """Extract the package name and pinned version (if any) from a requirement.

    Args:
        requirement: A raw PEP 508 requirement string (e.g. "requests>=2.0; python_version>='3.8'").

    Returns:
        Tuple of (package_name, current_version). current_version is None when
        the requirement has no version specifier.
    """
    spec = requirement.split(";", 1)[0]
    name_match = _NAME_RE.match(spec)
    name = name_match.group(1) if name_match else spec.strip()
    version_match = _VERSION_RE.search(spec)
    return name, version_match.group(1) if version_match else None


def load_pyproject_requirements(pyproject_path: Path) -> list[str]:
    """Collect all raw dependency strings from pyproject.toml, including every group.

    Reads `[project.dependencies]`, `[project.optional-dependencies]`, and
    `[dependency-groups]` (PEP 735). `include-group` references inside
    `[dependency-groups]` are skipped since the referenced group is read directly.

    Args:
        pyproject_path: Path to the pyproject.toml file.

    Returns:
        List of raw requirement strings (may contain duplicates).
    """
    data = tomllib.loads(pyproject_path.read_text())
    requirements: list[str] = list(data.get("project", {}).get("dependencies", []))

    for group_deps in data.get("project", {}).get("optional-dependencies", {}).values():
        requirements.extend(group_deps)

    for group_deps in data.get("dependency-groups", {}).values():
        requirements.extend(dep for dep in group_deps if isinstance(dep, str))

    return requirements


def collect_unique_requirements(raw_requirements: list[str]) -> dict[str, str | None]:
    """Deduplicate raw requirement strings by package name.

    Args:
        raw_requirements: Raw PEP 508 requirement strings, possibly with duplicates.

    Returns:
        Mapping of package name to its pinned version (None if unspecified).
    """
    unique: dict[str, str | None] = {}
    for requirement in raw_requirements:
        name, current_version = parse_requirement(requirement)
        unique.setdefault(name, current_version)
    return unique


def filter_requirements(
    requirements: dict[str, str | None],
    ignore: list[str],
    ignore_none_version: bool,
) -> list[str]:
    """Apply IGNORE_DEPENDENCIES / IGNORE_NONE_VERSION rules to a requirement map.

    Args:
        requirements: Mapping of package name to its pinned version.
        ignore: Package names to always skip.
        ignore_none_version: If True, skip packages with no version specifier.

    Returns:
        Sorted list of package names to check against PyPI.
    """
    names = []
    for name, current_version in requirements.items():
        if name in ignore:
            logger.debug("Skipping ignored dependency: %s", name)
            continue
        if ignore_none_version and current_version is None:
            logger.debug("Skipping dependency without a version specifier: %s", name)
            continue
        names.append(name)
    return sorted(names)


def get_latest_version(package: str) -> str:
    """Fetch the latest published version of a PyPI package.

    Args:
        package: The PyPI package name.

    Returns:
        The latest version string (e.g. "1.2.3").

    Raises:
        urllib.error.URLError: If the PyPI API request fails.
        KeyError: If the response JSON is missing expected fields.
    """
    url = f"https://pypi.org/pypi/{package}/json"
    with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310
        data = json.load(response)
    return data["info"]["version"]


def is_outdated(current_version: str | None, latest_version: str) -> bool:
    """Decide whether a dependency should be reported as outdated.

    Args:
        current_version: The version pinned in pyproject.toml, or None if unpinned.
        latest_version: The latest version published on PyPI.

    Returns:
        True if unpinned, or if the pinned version differs from the latest.
    """
    return current_version is None or current_version != latest_version


def check_outdated_dependencies(
    pyproject_path: Path,
    ignore: list[str],
    ignore_none_version: bool,
) -> list[tuple[str, str | None, str]]:
    """Check pyproject.toml dependencies (including groups) against PyPI.

    Only dependencies that are NOT already on the latest version are returned.
    Logs a warning (with traceback) for any package whose latest version
    cannot be fetched, and continues with the rest.

    Args:
        pyproject_path: Path to the pyproject.toml file.
        ignore: Package names to skip.
        ignore_none_version: If True, skip packages with no version specifier.

    Returns:
        List of (package_name, current_version, latest_version) tuples,
        one per dependency that is behind the latest PyPI release.
    """
    raw_requirements = load_pyproject_requirements(pyproject_path)
    unique_requirements = collect_unique_requirements(raw_requirements)
    names_to_check = filter_requirements(unique_requirements, ignore, ignore_none_version)

    outdated: list[tuple[str, str | None, str]] = []
    for name in names_to_check:
        current_version = unique_requirements[name]
        try:
            latest_version = get_latest_version(name)
        except Exception:
            logger.exception("Failed to fetch latest version for: %s", name)
            continue

        if is_outdated(current_version, latest_version):
            outdated.append((name, current_version, latest_version))
            logger.info("Outdated: %s (%s -> %s)", name, current_version or "unpinned", latest_version)
        else:
            logger.debug("Up to date: %s==%s", name, latest_version)

    return outdated
