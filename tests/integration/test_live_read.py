"""
Read-only tests of the MCP tools against the real GitHub API. Nothing is created or changed.

Needs GITHUB_ACCESS_TOKEN and GITHUB_TEST_REPO (loaded from .env). Uses an open PR in that repo if there is one.

Run:
    uv run pytest -m integration tests/integration/test_live_read.py
"""

import pytest
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from github_plus_mcp.server import create_server
from tests.integration.common import TEST_REPO, live_settings, requires_test_repo

pytestmark = [pytest.mark.integration, requires_test_repo]


@pytest.fixture(name="server", scope="module")
def server_fixture() -> FastMCP:
    return create_server(live_settings())


async def test_repo_and_branches(server: FastMCP) -> None:
    _, repo = await server.call_tool("github_get_repo", {})
    assert repo["full_name"].lower() == TEST_REPO.lower()
    _, branches = await server.call_tool("github_list_branches", {"limit": 1})
    assert branches["returned"] == 1
    assert branches["items"][0]["sha"]


async def test_open_pull_request_and_its_files(server: FastMCP) -> None:
    _, prs = await server.call_tool("github_list_pull_requests", {"state": "open", "limit": 5})
    if not prs["items"]:
        pytest.skip(f"{TEST_REPO} has no open pull requests")
    number = prs["items"][0]["number"]
    _, pr = await server.call_tool("github_get_pull_request", {"number": number})
    assert pr["state"] == "open" and pr["changed_files"] >= 1
    _, files = await server.call_tool("github_get_pull_request_files", {"number": number})
    assert files["returned"] == pr["changed_files"]
    assert all(f["filename"] for f in files["items"])


async def test_closed_list_reports_merged(server: FastMCP) -> None:
    _, prs = await server.call_tool("github_list_pull_requests", {"state": "closed", "limit": 20})
    assert {pr["state"] for pr in prs["items"]} <= {"closed", "merged"}


async def test_directory_and_file(server: FastMCP) -> None:
    _, entries = await server.call_tool("github_list_directory", {})  # lists come back as {"result": [...]}
    files = [e["path"] for e in entries["result"] if e["type"] == "file"]
    assert files
    _, content = await server.call_tool("github_get_file", {"path": files[0]})
    assert content["path"] == files[0] and content["size"] == len(content["content"])


async def test_missing_file_is_a_tool_error_with_hint(server: FastMCP) -> None:
    with pytest.raises(ToolError, match="GitHub error 404.*check the repo"):
        await server.call_tool("github_get_file", {"path": "no/such/file.txt"})


async def test_workflows(server: FastMCP) -> None:
    _, workflows = await server.call_tool("github_list_workflows", {})
    if not workflows["result"]:
        pytest.skip(f"{TEST_REPO} has no workflows")
    workflow = workflows["result"][0]["file"]
    _, runs = await server.call_tool("github_list_workflow_runs", {"workflow": workflow, "limit": 1})
    assert runs["returned"] <= 1
