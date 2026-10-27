from collections.abc import Iterator
from pathlib import Path

import pytest

_SAMPLE_PYPROJECT = """
[project]
dependencies = ["a>=1.0", "b"]

[project.optional-dependencies]
extra = ["c>=2.0"]

[dependency-groups]
dev = ["b", "err>=1.0", { include-group = "nested" }]
nested = ["c>=2.0"]
"""


@pytest.fixture
def sample_pyproject(tmp_path: Path) -> Iterator[Path]:
    """A temp pyproject.toml with dependencies spread across every group.

    Covers: plain dependencies, optional-dependencies, dependency-groups,
    a duplicate name across groups (b), and a PEP 735 include-group entry
    (nested), which callers must resolve by reading the referenced group directly.
    """
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(_SAMPLE_PYPROJECT)
    yield pyproject_path
