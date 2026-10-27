from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from python_github_plus.consts import MergeMethod

from github_plus_mcp.client import RepoClients
from github_plus_mcp.errors import tool_errors
from github_plus_mcp.models import WriteResult
from github_plus_mcp.tools.common import Repo

WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True)
IDEMPOTENT_WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True)
DESTRUCTIVE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=True)


def register_write_tools(mcp: FastMCP, clients: RepoClients) -> None:
    _register_ref_tools(mcp, clients)
    _register_pull_request_tools(mcp, clients)


def _register_ref_tools(mcp: FastMCP, clients: RepoClients) -> None:
    @mcp.tool(name="github_create_branch", annotations=WRITE)
    @tool_errors
    def github_create_branch(branch_name: str, repo: Repo = None, from_branch: str | None = None) -> WriteResult:
        """Create a branch from another branch (the default branch if omitted)."""
        ref = clients.get(repo).branch.create(branch_name, from_branch=from_branch)
        return WriteResult(ok=True, message=f"Created branch {branch_name}", sha=ref.object.sha)

    @mcp.tool(name="github_trigger_workflow", annotations=WRITE)
    @tool_errors
    def github_trigger_workflow(
        workflow: str, repo: Repo = None, branch: str | None = None, inputs: dict[str, str] | None = None
    ) -> WriteResult:
        """Run a workflow that has `workflow_dispatch` (name, file name or id) on a branch (default branch if
        omitted). Follow the run with github_get_workflow_run."""
        if (run := clients.get(repo).workflow.trigger(workflow, branch_name=branch, inputs=inputs)) is None:
            return WriteResult(ok=True, message=f"Triggered {workflow}; find the run with github_list_workflow_runs")
        return WriteResult(ok=True, message=f"Triggered {workflow}: run {run.id}", run_id=run.id, url=run.html_url)

    @mcp.tool(name="github_create_tag", annotations=WRITE)
    @tool_errors
    def github_create_tag(
        tag_name: str,
        repo: Repo = None,
        from_branch: str | None = None,
        sha: str | None = None,
        message: str | None = None,
    ) -> WriteResult:
        """Create an annotated tag on a commit `sha`, or on the head of `from_branch` (default branch if both
        are omitted)."""
        client = clients.get(repo)
        if sha and from_branch:
            raise ValueError("Pass either sha or from_branch, not both")
        tag = (
            client.tag.create_from_sha(tag_name, sha=sha, message=message)
            if sha
            else client.tag.create(tag_name, from_branch=from_branch, message=message)
        )
        return WriteResult(ok=True, message=f"Created tag {tag_name}", sha=tag.object.sha)


def _register_pull_request_tools(mcp: FastMCP, clients: RepoClients) -> None:
    @mcp.tool(name="github_create_pull_request", annotations=WRITE)
    @tool_errors
    def github_create_pull_request(
        title: str,
        from_branch: str,
        repo: Repo = None,
        target: str | None = None,
        body: str = "",
        draft: bool = False,
    ) -> WriteResult:
        """Open a pull request from `from_branch` into `target` (the default branch if omitted)."""
        pr = clients.get(repo).pull_request.create(title, from_branch, target=target, body=body, draft=draft)
        return WriteResult(ok=True, message=f"Opened PR #{pr.number}", number=pr.number, url=pr.html_url)

    @mcp.tool(name="github_comment_on_pull_request", annotations=WRITE)
    @tool_errors
    def github_comment_on_pull_request(number: int, comment: str, repo: Repo = None) -> WriteResult:
        """Add a comment to a pull request's conversation."""
        clients.get(repo).pull_request.add_comment(number, comment)
        return WriteResult(ok=True, message=f"Commented on PR #{number}", number=number)

    @mcp.tool(name="github_assign_pull_request", annotations=IDEMPOTENT_WRITE)
    @tool_errors
    def github_assign_pull_request(number: int, assignees: list[str], repo: Repo = None) -> WriteResult:
        """Add assignees (GitHub logins) to a pull request."""
        clients.get(repo).pull_request.assign(number, assignees)
        return WriteResult(ok=True, message=f"Assigned PR #{number} to {', '.join(assignees)}", number=number)

    @mcp.tool(name="github_approve_pull_request", annotations=WRITE)
    @tool_errors
    def github_approve_pull_request(number: int, repo: Repo = None, body: str = "Approved") -> WriteResult:
        """Submit an approving review. GitHub refuses approvals of your own pull requests."""
        clients.get(repo).pull_request.approve(number, body=body)
        return WriteResult(ok=True, message=f"Approved PR #{number}", number=number)

    @mcp.tool(name="github_close_pull_request", annotations=IDEMPOTENT_WRITE)
    @tool_errors
    def github_close_pull_request(number: int, repo: Repo = None) -> WriteResult:
        """Close a pull request without merging. It can be reopened."""
        clients.get(repo).pull_request.close(number)
        return WriteResult(ok=True, message=f"Closed PR #{number}", number=number)

    @mcp.tool(name="github_reopen_pull_request", annotations=IDEMPOTENT_WRITE)
    @tool_errors
    def github_reopen_pull_request(number: int, repo: Repo = None) -> WriteResult:
        """Reopen a closed (not merged) pull request."""
        clients.get(repo).pull_request.reopen(number)
        return WriteResult(ok=True, message=f"Reopened PR #{number}", number=number)


def register_destructive_tools(mcp: FastMCP, clients: RepoClients) -> None:
    @mcp.tool(name="github_merge_pull_request", annotations=DESTRUCTIVE)
    @tool_errors
    def github_merge_pull_request(
        number: int,
        repo: Repo = None,
        merge_method: MergeMethod = "merge",
        commit_title: str | None = None,
        commit_message: str | None = None,
    ) -> WriteResult:
        """Merge a pull request (merge, squash or rebase). Cannot be undone."""
        sha = clients.get(repo).pull_request.merge(
            number, merge_method=merge_method, commit_title=commit_title, commit_message=commit_message
        )
        return WriteResult(ok=True, message=f"Merged PR #{number} ({merge_method})", number=number, sha=sha)

    @mcp.tool(name="github_delete_branch", annotations=DESTRUCTIVE)
    @tool_errors
    def github_delete_branch(branch_name: str, repo: Repo = None) -> WriteResult:
        """Delete a branch. Cannot be undone; commits not on another branch become unreachable."""
        clients.get(repo).branch.delete(branch_name)
        return WriteResult(ok=True, message=f"Deleted branch {branch_name}")

    @mcp.tool(name="github_delete_tag", annotations=DESTRUCTIVE)
    @tool_errors
    def github_delete_tag(tag_name: str, repo: Repo = None) -> WriteResult:
        """Delete a tag. Cannot be undone."""
        clients.get(repo).tag.delete(tag_name)
        return WriteResult(ok=True, message=f"Deleted tag {tag_name}")
