from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    returned: int
    truncated: bool  # true when more exist than the requested limit


class RepoInfo(BaseModel):
    full_name: str
    description: str | None = None
    default_branch: str
    private: bool
    archived: bool
    language: str | None = None
    html_url: str


class BranchInfo(BaseModel):
    name: str
    sha: str
    protected: bool


class TagInfo(BaseModel):
    name: str
    sha: str


class PullRequestSummary(BaseModel):
    number: int
    title: str
    state: str  # open | closed | merged
    draft: bool
    author: str | None = None
    head: str
    base: str
    updated_at: datetime | None = None
    html_url: str


class PullRequestDetail(PullRequestSummary):
    body: str | None = None
    created_at: datetime | None = None
    merged_at: datetime | None = None
    mergeable: bool | None = None  # None while GitHub is still computing it
    mergeable_state: str | None = None
    commits: int
    additions: int
    deletions: int
    changed_files: int
    assignees: list[str] = []
    requested_reviewers: list[str] = []
    labels: list[str] = []


class PullRequestFile(BaseModel):
    filename: str
    status: str
    additions: int
    deletions: int
    previous_filename: str | None = None
    patch: str | None = None  # None for binary or very large diffs
    patch_truncated: bool = False


class FileContent(BaseModel):
    path: str
    ref: str | None = None
    size: int
    content: str
    truncated: bool


class DirEntry(BaseModel):
    name: str
    path: str
    type: str  # file | dir | symlink | submodule
    size: int


class WorkflowInfo(BaseModel):
    id: int
    name: str
    file: str
    state: str


class WorkflowRunInfo(BaseModel):
    id: int
    name: str | None = None
    run_number: int
    status: str | None = None
    conclusion: str | None = None
    event: str
    branch: str | None = None
    head_sha: str
    created_at: datetime | None = None
    html_url: str


class WriteResult(BaseModel):
    ok: bool
    message: str
    url: str | None = None
    number: int | None = None
    sha: str | None = None
    run_id: int | None = None
