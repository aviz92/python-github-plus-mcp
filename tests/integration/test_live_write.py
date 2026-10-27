"""
Write and destructive tests of the MCP tools against a real GitHub sandbox repository.

Creates temporary branches, a commit, pull requests and a tag, merges into a temporary branch (never the
default branch), and deletes everything through the MCP tools. Teardown fails if anything is left behind.
GitHub cannot delete pull requests, so each run leaves two closed PRs in the sandbox.

Needs GITHUB_ACCESS_TOKEN and GITHUB_TEST_REPO (loaded from .env).

Run:
    uv run pytest -m integration tests/integration/test_live_write.py
"""

import time
import uuid
from collections.abc import Iterator
from types import SimpleNamespace

import pytest
from github import GithubException
from mcp.server.fastmcp import FastMCP
from python_github_plus import GitHubClient

from github_plus_mcp.server import create_server
from tests.integration.common import TEST_REPO, live_settings, requires_test_repo

pytestmark = [pytest.mark.integration, requires_test_repo]

RUN_ID = f"{int(time.time())}-{uuid.uuid4().hex[:6]}"
PREFIX = f"github-plus-mcp-test/{RUN_ID}"
BASE, HEAD, TAG = f"{PREFIX}/base", f"{PREFIX}/head", f"{PREFIX}-tag"


@pytest.fixture(name="server", scope="module")
def server_fixture() -> FastMCP:
    return create_server(live_settings(github_mcp_read_only=False, github_mcp_enable_destructive=True))


@pytest.fixture(name="library", scope="module")
def library_fixture() -> Iterator[GitHubClient]:
    """The library directly: for the test commit (no MCP tool writes files) and for teardown."""
    client = GitHubClient(TEST_REPO)
    yield client
    for prefixed in [t.name for t in client.tag.list() if t.name.startswith(PREFIX)]:
        client.tag.delete(prefixed)
    for prefixed in sorted((b.name for b in client.branch.list() if b.name.startswith(PREFIX)), reverse=True):
        client.branch.delete(prefixed)
    leftovers = [b.name for b in client.branch.list() if b.name.startswith(PREFIX)]
    leftovers += [t.name for t in client.tag.list() if t.name.startswith(PREFIX)]
    assert not leftovers, f"teardown left these behind: {leftovers}"


@pytest.fixture(name="branches", scope="module")
async def branches_fixture(server: FastMCP, library: GitHubClient) -> SimpleNamespace:
    await server.call_tool("github_create_branch", {"branch_name": BASE})
    _, head = await server.call_tool("github_create_branch", {"branch_name": HEAD, "from_branch": BASE})
    library.project.get_info().create_file(
        f"github-plus-mcp-test/{RUN_ID}.txt", f"test commit {RUN_ID}", f"run {RUN_ID}\n", branch=HEAD
    )
    return SimpleNamespace(base=BASE, head=HEAD, base_sha=head["sha"])


@pytest.mark.asyncio(loop_scope="module")
async def test_pull_request_lifecycle(server: FastMCP, branches: SimpleNamespace, library: GitHubClient) -> None:
    _, created = await server.call_tool(
        "github_create_pull_request",
        {"title": f"[test] mcp {RUN_ID}", "from_branch": branches.head, "target": branches.base, "draft": True},
    )
    number = created["number"]
    await server.call_tool("github_comment_on_pull_request", {"number": number, "comment": f"comment {RUN_ID}"})
    login = library.github.get_user().login
    await server.call_tool("github_assign_pull_request", {"number": number, "assignees": [login]})

    _, pr = await server.call_tool("github_get_pull_request", {"number": number})
    assert (pr["draft"], pr["base"], pr["assignees"], pr["changed_files"]) == (True, branches.base, [login], 1)

    await server.call_tool("github_close_pull_request", {"number": number})
    _, pr = await server.call_tool("github_get_pull_request", {"number": number})
    assert pr["state"] == "closed"
    await server.call_tool("github_reopen_pull_request", {"number": number})
    _, pr = await server.call_tool("github_get_pull_request", {"number": number})
    assert pr["state"] == "open"
    await server.call_tool("github_close_pull_request", {"number": number})


@pytest.mark.asyncio(loop_scope="module")
async def test_squash_merge_into_temp_branch(server: FastMCP, branches: SimpleNamespace) -> None:
    _, created = await server.call_tool(
        "github_create_pull_request",
        {"title": f"[test] mcp merge {RUN_ID}", "from_branch": branches.head, "target": branches.base},
    )
    _, merged = await server.call_tool(
        "github_merge_pull_request", {"number": created["number"], "merge_method": "squash"}
    )
    _, pr = await server.call_tool("github_get_pull_request", {"number": created["number"]})
    assert pr["state"] == "merged"
    _, listed = await server.call_tool("github_list_branches", {"limit": 100})
    assert {"name": branches.base, "sha": merged["sha"]}.items() <= next(
        b for b in listed["items"] if b["name"] == branches.base
    ).items()


@pytest.mark.asyncio(loop_scope="module")
async def test_tag_create_and_delete(server: FastMCP, branches: SimpleNamespace, library: GitHubClient) -> None:
    _, created = await server.call_tool("github_create_tag", {"tag_name": TAG, "from_branch": branches.head})
    assert created["sha"] == library.branch.get(branches.head).commit.sha
    await server.call_tool("github_delete_tag", {"tag_name": TAG})
    with pytest.raises(GithubException) as err:
        library.project.get_info().get_git_ref(f"tags/{TAG}").complete()
    assert err.value.status == 404


@pytest.mark.asyncio(loop_scope="module")
async def test_delete_branches(server: FastMCP, branches: SimpleNamespace) -> None:
    for name in (branches.head, branches.base):
        await server.call_tool("github_delete_branch", {"branch_name": name})
    _, listed = await server.call_tool("github_list_branches", {"limit": 100})
    assert not [b for b in listed["items"] if b["name"].startswith(PREFIX)]
