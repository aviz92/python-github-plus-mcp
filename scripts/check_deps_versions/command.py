import argparse
import sys
from pathlib import Path
from typing import Any

from python_base_command import BaseCommand, CommandError

from scripts.check_deps_versions.const import IGNORE_DEPENDENCIES, IGNORE_NONE_VERSION
from scripts.check_deps_versions.service import (
    DEFAULT_PYPROJECT_PATH,
    check_outdated_dependencies,
)


class Command(BaseCommand):
    help = "Check pyproject.toml dependencies (including all groups) against the latest PyPI versions"
    version = "0.0.1"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--pyproject",
            type=Path,
            default=DEFAULT_PYPROJECT_PATH,
            help="Path to pyproject.toml (default: %(default)s)",
        )
        parser.add_argument(
            "--ignore",
            nargs="*",
            default=IGNORE_DEPENDENCIES,
            metavar="PACKAGE",
            help="Dependency names to skip (default: %(default)s)",
        )
        parser.add_argument(
            "--ignore-none-version",
            action=argparse.BooleanOptionalAction,
            default=IGNORE_NONE_VERSION,
            help="Skip dependencies with no version specifier (default: %(default)s)",
        )

    def handle(self, **kwargs: Any) -> None:
        pyproject_path: Path = kwargs["pyproject"]
        ignore: list[str] = kwargs["ignore"] or []
        ignore_none_version: bool = kwargs["ignore_none_version"]

        if not pyproject_path.is_file():
            raise CommandError(f"pyproject.toml not found at: {pyproject_path}")

        self.logger.step("Checking dependency versions in: %s", pyproject_path)

        try:
            outdated = check_outdated_dependencies(pyproject_path, ignore, ignore_none_version)
        except Exception as exc:
            raise CommandError(f"Failed to check dependency versions: {exc}") from exc

        if not outdated:
            self.logger.step("All dependencies are up to date.")
            return

        self.logger.step("%d dependencies not on the latest version:", len(outdated))
        for name, current_version, latest_version in outdated:
            self.logger.step("  %s: %s -> %s", name, current_version or "unpinned", latest_version)


def main(argv: list[str] | None = None) -> None:
    Command().run_from_argv(argv if argv is not None else sys.argv)


if __name__ == "__main__":
    main()

    # Example usage for testing the command directly (uncomment to run):
    # Command().handle(
    #     pyproject=Path('/Users/avizaguri-macbook/Development/aviz92/dev-template-repository/pyproject.toml'),
    #     ignore=[],
    #     ignore_none_version=False
    # )
