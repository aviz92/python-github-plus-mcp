import pytest
from github import GithubException
from mcp.server.fastmcp.exceptions import ToolError

from github_plus_mcp.errors import to_tool_error


def test_validation_details_are_included() -> None:
    err = GithubException(
        422, {"message": "Validation Failed", "errors": [{"message": "A pull request already exists"}]}, None
    )
    assert str(to_tool_error(err)) == "GitHub error 422: Validation Failed; A pull request already exists"


def test_403_names_the_missing_permission() -> None:
    err = GithubException(
        403, {"message": "Resource not accessible"}, {"X-Accepted-GitHub-Permissions": "contents=write"}
    )
    assert "the token needs: contents=write" in str(to_tool_error(err))


def test_404_adds_a_hint() -> None:
    assert "check the repo" in str(to_tool_error(GithubException(404, {"message": "Not Found"}, None)))


def test_non_dict_data() -> None:
    assert str(to_tool_error(GithubException(500, "boom", None))) == "GitHub error 500: boom"


def test_value_error_passes_through() -> None:
    assert (
        str(to_tool_error(ValueError("repo_full_name must be 'owner/name'"))) == "repo_full_name must be 'owner/name'"
    )


def test_tool_error_is_kept_and_others_are_named() -> None:
    original = ToolError("x")
    assert to_tool_error(original) is original
    assert str(to_tool_error(KeyError("k"))) == "Unexpected error: KeyError: 'k'"


@pytest.mark.parametrize("status", [401, 500])
def test_status_in_message(status: int) -> None:
    assert str(to_tool_error(GithubException(status, {"message": "m"}, None))).startswith(f"GitHub error {status}")
