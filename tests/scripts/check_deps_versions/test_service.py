from pathlib import Path

import pytest

from scripts.check_deps_versions.const import IGNORE_DEPENDENCIES, IGNORE_NONE_VERSION
from scripts.check_deps_versions.service import (
    DEFAULT_PYPROJECT_PATH,
    check_outdated_dependencies,
    collect_unique_requirements,
    filter_requirements,
    is_outdated,
    load_pyproject_requirements,
    parse_requirement,
)


class TestParseRequirement:
    @pytest.mark.parametrize(
        "requirement,expected",
        [
            ("custom-python-logger>=4.0.2", ("custom-python-logger", "4.0.2")),
            ("python-base-command", ("python-base-command", None)),
            ("pkg==1.2.3; python_version>='3.8'", ("pkg", "1.2.3")),
            ("pkg[extra]>=2.0", ("pkg", "2.0")),
            ("pkg~=1.0", ("pkg", "1.0")),
        ],
    )
    def test_parse_requirement_returns_name_and_version(
        self, requirement: str, expected: tuple[str, str | None]
    ) -> None:
        result = parse_requirement(requirement)
        assert result == expected, f"Expected {expected}, got {result} for {requirement!r}"


class TestLoadPyprojectRequirements:
    def test_load_pyproject_requirements_collects_every_group(self, sample_pyproject: Path) -> None:
        requirements = load_pyproject_requirements(sample_pyproject)

        assert requirements.count("a>=1.0") == 1, "dependencies entry missing"
        assert requirements.count("c>=2.0") == 2, "optional-dependencies + nested group entries missing"
        assert requirements.count("b") == 2, "duplicate across dependencies and dependency-groups missing"
        assert requirements.count("err>=1.0") == 1, "dependency-groups entry missing"
        assert not any(isinstance(req, dict) for req in requirements), "include-group dict leaked into output"


class TestCollectUniqueRequirements:
    def test_collect_unique_requirements_dedupes_by_name(self) -> None:
        result = collect_unique_requirements(["a>=1.0", "a>=2.0", "b"])
        assert result == {"a": "1.0", "b": None}, f"Unexpected dedup result: {result}"

    def test_collect_unique_requirements_from_sample_pyproject(self, sample_pyproject: Path) -> None:
        raw = load_pyproject_requirements(sample_pyproject)
        result = collect_unique_requirements(raw)
        assert result == {"a": "1.0", "b": None, "c": "2.0", "err": "1.0"}, f"Unexpected result: {result}"


class TestFilterRequirements:
    def test_filter_requirements_applies_ignore_and_none_version_rules(self) -> None:
        requirements = {"a": "1.0", "b": None, "c": "2.0"}
        result = filter_requirements(requirements, ignore=["c"], ignore_none_version=True)
        assert result == ["a"], f"Expected only 'a' to survive filtering, got {result}"

    def test_filter_requirements_keeps_none_version_when_disabled(self) -> None:
        requirements = {"a": "1.0", "b": None}
        result = filter_requirements(requirements, ignore=[], ignore_none_version=False)
        assert result == ["a", "b"], f"Expected both entries kept, got {result}"


class TestIsOutdated:
    @pytest.mark.parametrize(
        "current_version,latest_version,expected",
        [
            (None, "1.0", True),
            ("1.0", "1.0", False),
            ("1.0", "2.0", True),
        ],
    )
    def test_is_outdated_compares_current_to_latest(
        self, current_version: str | None, latest_version: str, expected: bool
    ) -> None:
        result = is_outdated(current_version, latest_version)
        assert result is expected, f"Expected {expected} for ({current_version!r}, {latest_version!r})"


class TestCheckOutdatedDependencies:
    @pytest.fixture(autouse=True)
    def mock_pypi(self, monkeypatch: pytest.MonkeyPatch) -> None:
        latest_versions = {"a": "1.0", "b": "9.9", "c": "5.0"}

        def fake_get_latest_version(package: str) -> str:
            if package == "err":
                raise RuntimeError("PyPI lookup failed")
            return latest_versions[package]

        monkeypatch.setattr(
            "scripts.check_deps_versions.service.get_latest_version",
            fake_get_latest_version,
        )

    def test_check_outdated_dependencies_returns_only_stale_and_unpinned(self, sample_pyproject: Path) -> None:
        result = check_outdated_dependencies(sample_pyproject, ignore=[], ignore_none_version=False)
        assert result == [
            ("b", None, "9.9"),
            ("c", "2.0", "5.0"),
        ], f"Unexpected outdated list: {result}"

    def test_check_outdated_dependencies_skips_ignored_and_unpinned(self, sample_pyproject: Path) -> None:
        result = check_outdated_dependencies(sample_pyproject, ignore=["c"], ignore_none_version=True)
        assert not result, f"Expected no results once 'b' (unpinned) and 'c' (ignored) are excluded, got {result}"

    def test_check_outdated_dependencies_skips_package_whose_lookup_fails(self, sample_pyproject: Path) -> None:
        result = check_outdated_dependencies(sample_pyproject, ignore=[], ignore_none_version=False)
        assert all(name != "err" for name, _, _ in result), "Failed lookup should be skipped, not raised"


class TestProjectDependenciesAreLatest:  # The real network test, not a unit test
    def test_all_project_dependencies_are_on_latest_pypi_version(self) -> None:
        """Guard test: fails if any real dependency in this repo's pyproject.toml
        is behind the latest published PyPI release. Hits the network."""
        outdated = check_outdated_dependencies(
            pyproject_path=DEFAULT_PYPROJECT_PATH,
            ignore=IGNORE_DEPENDENCIES,
            ignore_none_version=IGNORE_NONE_VERSION,
        )
        details = ", ".join(f"{name} ({current or 'unpinned'} -> {latest})" for name, current, latest in outdated)
        assert not outdated, f"Outdated dependencies found in pyproject.toml: {details}"
