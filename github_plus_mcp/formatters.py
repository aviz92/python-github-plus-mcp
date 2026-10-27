"""Shape PyGithub objects into small models for a model. GitHub logic lives in python-github-plus."""

import os

from github.Branch import Branch
from github.ContentFile import ContentFile
from github.File import File
from github.PullRequest import PullRequest
from github.Repository import Repository
from github.Tag import Tag
from github.Workflow import Workflow
from github.WorkflowRun import WorkflowRun

from github_plus_mcp.models import (
    BranchInfo,
    DirEntry,
    PullRequestDetail,
    PullRequestFile,
    PullRequestSummary,
    RepoInfo,
    TagInfo,
    WorkflowInfo,
    WorkflowRunInfo,
)

MAX_PATCH_CHARS = 4_000


def format_repo(repo: Repository) -> RepoInfo:
    return RepoInfo(
        full_name=repo.full_name,
        description=repo.description,
        default_branch=repo.default_branch,
        private=repo.private,
        archived=repo.archived,
        language=repo.language,
        html_url=repo.html_url,
    )


def format_branch(branch: Branch) -> BranchInfo:
    return BranchInfo(name=branch.name, sha=branch.commit.sha, protected=branch.protected)


def format_tag(tag: Tag) -> TagInfo:
    return TagInfo(name=tag.name, sha=tag.commit.sha)


def pr_state(pr: PullRequest) -> str:
    # list payloads carry merged_at but not `merged`; reading `merged` there would fetch every PR again
    return "merged" if pr.merged_at else pr.state


def format_pr_summary(pr: PullRequest) -> PullRequestSummary:
    return PullRequestSummary(
        number=pr.number,
        title=pr.title,
        state=pr_state(pr),
        draft=bool(pr.draft),
        author=pr.user.login if pr.user else None,
        head=pr.head.ref,
        base=pr.base.ref,
        updated_at=pr.updated_at,
        html_url=pr.html_url,
    )


def format_pr_detail(pr: PullRequest) -> PullRequestDetail:
    return PullRequestDetail(
        **format_pr_summary(pr).model_dump(),
        body=pr.body,
        created_at=pr.created_at,
        merged_at=pr.merged_at,
        mergeable=pr.mergeable,
        mergeable_state=pr.mergeable_state,
        commits=pr.commits,
        additions=pr.additions,
        deletions=pr.deletions,
        changed_files=pr.changed_files,
        assignees=[user.login for user in pr.assignees or []],
        requested_reviewers=[user.login for user in pr.requested_reviewers or []],
        labels=[label.name for label in pr.labels or []],
    )


def format_pr_file(file: File) -> PullRequestFile:
    patch = file.patch
    truncated = patch is not None and len(patch) > MAX_PATCH_CHARS
    return PullRequestFile(
        filename=file.filename,
        status=file.status,
        additions=file.additions,
        deletions=file.deletions,
        previous_filename=file.previous_filename,
        patch=patch[:MAX_PATCH_CHARS] if truncated else patch,
        patch_truncated=truncated,
    )


def format_dir_entry(entry: ContentFile) -> DirEntry:
    return DirEntry(name=entry.name, path=entry.path, type=entry.type, size=entry.size)


def format_workflow(workflow: Workflow) -> WorkflowInfo:
    return WorkflowInfo(id=workflow.id, name=workflow.name, file=os.path.basename(workflow.path), state=workflow.state)


def format_run(run: WorkflowRun) -> WorkflowRunInfo:
    return WorkflowRunInfo(
        id=run.id,
        name=run.name,
        run_number=run.run_number,
        status=run.status,
        conclusion=run.conclusion,
        event=run.event,
        branch=run.head_branch,
        head_sha=run.head_sha,
        created_at=run.created_at,
        html_url=run.html_url,
    )
