from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from github import GithubException
from mcp.server.fastmcp.exceptions import ToolError

from github_plus_mcp.server import create_server
from tests.common import WHEN, make_pr, make_settings

READ_TOOLS = {
    "github_get_repo",
    "github_list_branches",
    "github_list_tags",
    "github_list_pull_requests",
    "github_get_pull_request",
    "github_get_pull_request_files",
    "github_get_file",
    "github_list_directory",
    "github_list_workflows",
    "github_list_workflow_runs",
    "github_get_workflow_run",
}


def branch(name: str) -> SimpleNamespace:
    return SimpleNamespace(name=name, commit=SimpleNamespace(sha=f"sha-{name}"), protected=False)


async def test_read_only_by_default_with_prefixed_read_only_tools() -> None:
    tools = await create_server(make_settings()).list_tools()
    assert {t.name for t in tools} == READ_TOOLS
    assert all(t.annotations.readOnlyHint and not t.annotations.destructiveHint for t in tools)


async def test_instructions_mention_the_default_repo() -> None:
    assert "defaults to owner/default" in create_server(make_settings()).instructions


async def test_repo_argument_and_default(gh: MagicMock) -> None:
    gh.project.get_info.return_value = SimpleNamespace(
        full_name="owner/x",
        description=None,
        default_branch="main",
        private=False,
        archived=False,
        language="Python",
        html_url="https://github.com/owner/x",
    )
    server = create_server(make_settings())
    _, result = await server.call_tool("github_get_repo", {"repo": "owner/x"})
    assert result["default_branch"] == "main"
    assert gh.cls.call_args.args == ("owner/x",)
    await server.call_tool("github_get_repo", {})
    gh.for_repo.assert_called_once_with("owner/default")


async def test_list_asks_for_one_extra_and_flags_truncated(gh: MagicMock) -> None:
    gh.branch.list.return_value = [branch("a"), branch("b"), branch("c")]
    _, result = await create_server(make_settings()).call_tool("github_list_branches", {"limit": 2})
    gh.branch.list.assert_called_once_with(limit=3)
    assert (result["returned"], result["truncated"]) == (2, True)
    assert [b["name"] for b in result["items"]] == ["a", "b"]


async def test_list_not_truncated(gh: MagicMock) -> None:
    gh.branch.list.return_value = [branch("a")]
    _, result = await create_server(make_settings()).call_tool("github_list_branches", {"limit": 2})
    assert (result["returned"], result["truncated"]) == (1, False)


async def test_limit_is_clamped_to_max_results(gh: MagicMock) -> None:
    gh.tag.list.return_value = []
    server = create_server(make_settings(github_mcp_max_results=5))
    await server.call_tool("github_list_tags", {"limit": 999})
    gh.tag.list.assert_called_once_with(limit=6)
    await server.call_tool("github_list_tags", {"limit": 0})
    assert gh.tag.list.call_args.kwargs == {"limit": 2}


async def test_list_pull_requests_passes_filters(gh: MagicMock) -> None:
    gh.pull_request.list.return_value = [make_pr(1), make_pr(2, state="closed", merged_at=WHEN)]
    _, result = await create_server(make_settings()).call_tool(
        "github_list_pull_requests", {"state": "all", "base": "main"}
    )
    gh.pull_request.list.assert_called_once_with(state="all", base="main", limit=21)
    assert [pr["state"] for pr in result["items"]] == ["open", "merged"]


async def test_get_pull_request(gh: MagicMock) -> None:
    gh.pull_request.get_info.return_value = make_pr(7)
    _, result = await create_server(make_settings()).call_tool("github_get_pull_request", {"number": 7})
    gh.pull_request.get_info.assert_called_once_with(7)
    assert (result["number"], result["mergeable_state"], result["labels"]) == (7, "clean", ["bug"])


async def test_get_file_is_capped(gh: MagicMock) -> None:
    gh.file.fetch_content.return_value = "abcdef"
    server = create_server(make_settings(github_mcp_max_file_chars=4))
    _, result = await server.call_tool("github_get_file", {"path": "a.txt", "ref": "dev"})
    gh.file.fetch_content.assert_called_once_with("a.txt", ref="dev")
    assert (result["content"], result["size"], result["truncated"]) == ("abcd", 6, True)


async def test_get_file_on_directory_points_to_list_directory(gh: MagicMock) -> None:
    gh.file.fetch_content.side_effect = ValueError("❌ 'src' is a directory; use list_dir")
    with pytest.raises(ToolError, match="is a directory"):
        await create_server(make_settings()).call_tool("github_get_file", {"path": "src"})


async def test_github_error_becomes_tool_error(gh: MagicMock) -> None:
    gh.pull_request.get_info.side_effect = GithubException(404, {"message": "Not Found"}, None)
    with pytest.raises(ToolError, match="GitHub error 404: Not Found"):
        await create_server(make_settings()).call_tool("github_get_pull_request", {"number": 999})


async def test_missing_repo_without_default_is_a_tool_error() -> None:
    server = create_server(make_settings(github_mcp_default_repo=""))
    with pytest.raises(ToolError, match="pass repo as 'owner/name'"):
        await server.call_tool("github_list_workflows", {})


async def test_workflow_runs(gh: MagicMock) -> None:
    gh.workflow.list_runs.return_value = [
        SimpleNamespace(
            id=11,
            name="CI",
            run_number=3,
            status="completed",
            conclusion="success",
            event="push",
            head_branch="main",
            head_sha="abc",
            created_at=WHEN,
            html_url="https://github.com/owner/default/actions/runs/11",
        )
    ]
    _, result = await create_server(make_settings()).call_tool(
        "github_list_workflow_runs", {"workflow": "ci.yml", "branch": "main", "limit": 1}
    )
    gh.workflow.list_runs.assert_called_once_with("ci.yml", branch="main", limit=2)
    assert result["items"][0]["conclusion"] == "success"
