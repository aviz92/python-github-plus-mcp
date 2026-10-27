from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(name="gh")
def gh_fixture() -> Iterator[MagicMock]:
    """A mocked python-github-plus GitHubClient; `gh.cls` is the patched class, for constructor checks."""
    client = MagicMock()
    client.for_repo.return_value = client
    with patch("github_plus_mcp.client.GitHubClient", return_value=client) as cls:
        client.cls = cls
        yield client
