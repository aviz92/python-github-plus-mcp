from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from github_plus_mcp.client import RepoClients
from github_plus_mcp.errors import tool_errors
from github_plus_mcp.formatters import (
    format_branch,
    format_dir_entry,
    format_pr_detail,
    format_pr_file,
    format_pr_summary,
    format_repo,
    format_run,
    format_tag,
    format_workflow,
)
from github_plus_mcp.models import (
    BranchInfo,
    DirEntry,
    FileContent,
    Page,
    PullRequestDetail,
    PullRequestFile,
    PullRequestSummary,
    RepoInfo,
    TagInfo,
    WorkflowInfo,
    WorkflowRunInfo,
)
from github_plus_mcp.settings import Settings
from github_plus_mcp.tools.common import Ref, Repo, clamp, paginate

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=True)


def register_read_tools(mcp: FastMCP, settings: Settings, clients: RepoClients) -> None:
    _register_repo_tools(mcp, settings, clients)
    _register_pull_request_tools(mcp, settings.github_mcp_max_results, clients)
    _register_workflow_tools(mcp, settings.github_mcp_max_results, clients)


def _register_repo_tools(mcp: FastMCP, settings: Settings, clients: RepoClients) -> None:
    max_results = settings.github_mcp_max_results

    @mcp.tool(name="github_get_repo", annotations=READ_ONLY)
    @tool_errors
    def github_get_repo(repo: Repo = None) -> RepoInfo:
        """Get a repository's basic info, including its default branch."""
        return format_repo(clients.get(repo).project.get_info())

    @mcp.tool(name="github_list_branches", annotations=READ_ONLY)
    @tool_errors
    def github_list_branches(repo: Repo = None, limit: int = 30) -> Page[BranchInfo]:
        """List branches with their head commit sha."""
        limit = clamp(limit, max_results)
        return Page[BranchInfo](**paginate(clients.get(repo).branch.list(limit=limit + 1), limit, format_branch))

    @mcp.tool(name="github_list_tags", annotations=READ_ONLY)
    @tool_errors
    def github_list_tags(repo: Repo = None, limit: int = 30) -> Page[TagInfo]:
        """List tags, newest first, with the commit each points to."""
        limit = clamp(limit, max_results)
        return Page[TagInfo](**paginate(clients.get(repo).tag.list(limit=limit + 1), limit, format_tag))

    @mcp.tool(name="github_get_file", annotations=READ_ONLY)
    @tool_errors
    def github_get_file(path: str, repo: Repo = None, ref: Ref = None) -> FileContent:
        """Read a text file. Long files are cut and flagged `truncated`. For a directory use github_list_directory."""
        content = clients.get(repo).file.fetch_content(path, ref=ref)
        cap = settings.github_mcp_max_file_chars
        return FileContent(path=path, ref=ref, size=len(content), content=content[:cap], truncated=len(content) > cap)

    @mcp.tool(name="github_list_directory", annotations=READ_ONLY)
    @tool_errors
    def github_list_directory(path: str = "", repo: Repo = None, ref: Ref = None) -> list[DirEntry]:
        """List a directory ("" is the repo root)."""
        return [format_dir_entry(entry) for entry in clients.get(repo).file.list_dir(path, ref=ref)]


def _register_pull_request_tools(mcp: FastMCP, max_results: int, clients: RepoClients) -> None:
    @mcp.tool(name="github_list_pull_requests", annotations=READ_ONLY)
    @tool_errors
    def github_list_pull_requests(
        repo: Repo = None, state: Literal["open", "closed", "all"] = "open", base: str | None = None, limit: int = 20
    ) -> Page[PullRequestSummary]:
        """List pull requests, newest first. `state` "closed" includes merged ones (state "merged" in results)."""
        limit = clamp(limit, max_results)
        found = clients.get(repo).pull_request.list(state=state, base=base, limit=limit + 1)
        return Page[PullRequestSummary](**paginate(found, limit, format_pr_summary))

    @mcp.tool(name="github_get_pull_request", annotations=READ_ONLY)
    @tool_errors
    def github_get_pull_request(number: int, repo: Repo = None) -> PullRequestDetail:
        """Get one pull request: description, mergeability, size, assignees, reviewers and labels."""
        return format_pr_detail(clients.get(repo).pull_request.get_info(number))

    @mcp.tool(name="github_get_pull_request_files", annotations=READ_ONLY)
    @tool_errors
    def github_get_pull_request_files(number: int, repo: Repo = None, limit: int = 50) -> Page[PullRequestFile]:
        """List the files a pull request changes, with their diff (long diffs are cut, `patch_truncated`)."""
        limit = clamp(limit, max_results)
        found = clients.get(repo).pull_request.files(number, limit=limit + 1)
        return Page[PullRequestFile](**paginate(found, limit, format_pr_file))


def _register_workflow_tools(mcp: FastMCP, max_results: int, clients: RepoClients) -> None:
    @mcp.tool(name="github_list_workflows", annotations=READ_ONLY)
    @tool_errors
    def github_list_workflows(repo: Repo = None) -> list[WorkflowInfo]:
        """List GitHub Actions workflows with their id and file name."""
        return [format_workflow(workflow) for workflow in clients.get(repo).workflow.list()]

    @mcp.tool(name="github_list_workflow_runs", annotations=READ_ONLY)
    @tool_errors
    def github_list_workflow_runs(
        workflow: str, repo: Repo = None, branch: str | None = None, limit: int = 10
    ) -> Page[WorkflowRunInfo]:
        """List runs of a workflow, newest first. `workflow` is its name, file name (ci.yml) or id."""
        limit = clamp(limit, max_results)
        found = clients.get(repo).workflow.list_runs(workflow, branch=branch, limit=limit + 1)
        return Page[WorkflowRunInfo](**paginate(found, limit, format_run))

    @mcp.tool(name="github_get_workflow_run", annotations=READ_ONLY)
    @tool_errors
    def github_get_workflow_run(run_id: int, repo: Repo = None) -> WorkflowRunInfo:
        """Get one workflow run's status and conclusion. Poll this to follow a run."""
        return format_run(clients.get(repo).workflow.get_run(run_id))
