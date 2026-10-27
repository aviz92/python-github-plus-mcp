from unittest.mock import MagicMock

import pytest

from github_plus_mcp.client import RepoClients
from tests.common import make_settings


def test_first_client_gets_credentials_from_settings(gh: MagicMock) -> None:
    RepoClients(make_settings(github_base_url="https://ghe.example.com/api/v3")).get("owner/a")
    gh.cls.assert_called_once_with("owner/a", access_token="t", base_url="https://ghe.example.com/api/v3")


def test_empty_settings_fall_back_to_library_env_handling(gh: MagicMock) -> None:
    RepoClients(make_settings(github_access_token="")).get("owner/a")
    gh.cls.assert_called_once_with("owner/a", access_token=None, base_url=None)


def test_other_repos_share_the_first_connection(gh: MagicMock) -> None:
    clients = RepoClients(make_settings())
    clients.get("owner/a")
    clients.get("owner/b")
    gh.cls.assert_called_once()
    gh.for_repo.assert_called_once_with("owner/b")


def test_clients_are_cached_case_insensitively(gh: MagicMock) -> None:
    clients = RepoClients(make_settings())
    assert clients.get("Owner/A") is clients.get("owner/a")
    gh.cls.assert_called_once()
    gh.for_repo.assert_not_called()


def test_default_repo_is_used_when_none_given(gh: MagicMock) -> None:
    RepoClients(make_settings()).get(None)
    assert gh.cls.call_args.args == ("owner/default",)


def test_no_repo_and_no_default_raises() -> None:
    with pytest.raises(ValueError, match="GITHUB_MCP_DEFAULT_REPO"):
        RepoClients(make_settings(github_mcp_default_repo="")).get(None)
