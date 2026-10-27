from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from github_plus_mcp.server import create_server
from tests.common import DESTRUCTIVE, WRITABLE, make_settings

WRITE_TOOLS = {
    "github_create_branch",
    "github_create_pull_request",
    "github_comment_on_pull_request",
    "github_assign_pull_request",
    "github_approve_pull_request",
    "github_close_pull_request",
    "github_reopen_pull_request",
    "github_trigger_workflow",
    "github_create_tag",
}
DESTRUCTIVE_TOOLS = {"github_merge_pull_request", "github_delete_branch", "github_delete_tag"}


async def tool_names(**settings: object) -> set[str]:
    return {t.name for t in await create_server(make_settings(**settings)).list_tools()}


async def test_write_tools_only_when_not_read_only() -> None:
    writable = await tool_names(**WRITABLE)
    assert WRITE_TOOLS <= writable
    assert not DESTRUCTIVE_TOOLS & writable


async def test_destructive_tools_need_both_flags() -> None:
    assert DESTRUCTIVE_TOOLS <= await tool_names(**DESTRUCTIVE)
    assert not DESTRUCTIVE_TOOLS & await tool_names(github_mcp_enable_destructive=True)  # still read-only


async def test_destructive_annotations() -> None:
    tools = {t.name: t for t in await create_server(make_settings(**DESTRUCTIVE)).list_tools()}
    assert all(tools[name].annotations.destructiveHint for name in DESTRUCTIVE_TOOLS)
    assert not any(tools[name].annotations.destructiveHint for name in WRITE_TOOLS)


async def test_create_pull_request(gh: MagicMock) -> None:
    gh.pull_request.create.return_value = SimpleNamespace(number=5, html_url="https://github.com/o/r/pull/5")
    _, result = await create_server(make_settings(**WRITABLE)).call_tool(
        "github_create_pull_request", {"title": "T", "from_branch": "feature", "body": "B", "draft": True}
    )
    gh.pull_request.create.assert_called_once_with("T", "feature", target=None, body="B", draft=True)
    assert (result["number"], result["url"]) == (5, "https://github.com/o/r/pull/5")


async def test_create_branch_returns_sha(gh: MagicMock) -> None:
    gh.branch.create.return_value = SimpleNamespace(object=SimpleNamespace(sha="abc"))
    _, result = await create_server(make_settings(**WRITABLE)).call_tool(
        "github_create_branch", {"branch_name": "feature/x", "from_branch": "dev"}
    )
    gh.branch.create.assert_called_once_with("feature/x", from_branch="dev")
    assert result["sha"] == "abc"


async def test_assign_and_comment(gh: MagicMock) -> None:
    server = create_server(make_settings(**WRITABLE))
    await server.call_tool("github_assign_pull_request", {"number": 3, "assignees": ["a", "b"]})
    gh.pull_request.assign.assert_called_once_with(3, ["a", "b"])
    await server.call_tool("github_comment_on_pull_request", {"number": 3, "comment": "hi"})
    gh.pull_request.add_comment.assert_called_once_with(3, "hi")


async def test_trigger_workflow_with_and_without_run(gh: MagicMock) -> None:
    server = create_server(make_settings(**WRITABLE))
    gh.workflow.trigger.return_value = SimpleNamespace(id=42, html_url="https://github.com/o/r/actions/runs/42")
    _, result = await server.call_tool("github_trigger_workflow", {"workflow": "ci.yml", "inputs": {"a": "1"}})
    gh.workflow.trigger.assert_called_once_with("ci.yml", branch_name=None, inputs={"a": "1"})
    assert result["run_id"] == 42
    gh.workflow.trigger.return_value = None
    _, result = await server.call_tool("github_trigger_workflow", {"workflow": "ci.yml"})
    assert result["run_id"] is None and "github_list_workflow_runs" in result["message"]


async def test_create_tag_from_sha_or_branch(gh: MagicMock) -> None:
    gh.tag.create_from_sha.return_value = gh.tag.create.return_value = SimpleNamespace(object=SimpleNamespace(sha="c1"))
    server = create_server(make_settings(**WRITABLE))
    await server.call_tool("github_create_tag", {"tag_name": "v1", "sha": "c1"})
    gh.tag.create_from_sha.assert_called_once_with("v1", sha="c1", message=None)
    await server.call_tool("github_create_tag", {"tag_name": "v2", "from_branch": "dev", "message": "m"})
    gh.tag.create.assert_called_once_with("v2", from_branch="dev", message="m")


async def test_create_tag_rejects_sha_and_branch_together(gh: MagicMock) -> None:
    with pytest.raises(ToolError, match="either sha or from_branch"):
        await create_server(make_settings(**WRITABLE)).call_tool(
            "github_create_tag", {"tag_name": "v1", "sha": "c1", "from_branch": "dev"}
        )
    gh.tag.create_from_sha.assert_not_called()


async def test_merge(gh: MagicMock) -> None:
    gh.pull_request.merge.return_value = "merge-sha"
    _, result = await create_server(make_settings(**DESTRUCTIVE)).call_tool(
        "github_merge_pull_request", {"number": 9, "merge_method": "squash"}
    )
    gh.pull_request.merge.assert_called_once_with(9, merge_method="squash", commit_title=None, commit_message=None)
    assert result["sha"] == "merge-sha"


async def test_merge_rejects_unknown_method(gh: MagicMock) -> None:
    with pytest.raises(ToolError):
        await create_server(make_settings(**DESTRUCTIVE)).call_tool(
            "github_merge_pull_request", {"number": 9, "merge_method": "fast-forward"}
        )
    gh.pull_request.merge.assert_not_called()


async def test_delete_branch_and_tag(gh: MagicMock) -> None:
    server = create_server(make_settings(**DESTRUCTIVE))
    await server.call_tool("github_delete_branch", {"branch_name": "old"})
    gh.branch.delete.assert_called_once_with("old")
    await server.call_tool("github_delete_tag", {"tag_name": "v0"})
    gh.tag.delete.assert_called_once_with("v0")
