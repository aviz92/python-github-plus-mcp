from types import SimpleNamespace

from github_plus_mcp.formatters import MAX_PATCH_CHARS, format_pr_detail, format_pr_file, format_pr_summary
from tests.common import WHEN, make_pr


def test_pr_state_uses_merged_at_not_merged() -> None:
    pr = make_pr(state="closed", merged_at=WHEN)  # no `merged` attribute, as in list payloads
    assert format_pr_summary(pr).state == "merged"
    assert format_pr_summary(make_pr(state="closed")).state == "closed"


def test_pr_detail_flattens_people_and_labels() -> None:
    detail = format_pr_detail(make_pr())
    assert (detail.author, detail.assignees, detail.requested_reviewers, detail.labels) == (
        "author",
        ["a"],
        ["r"],
        ["bug"],
    )
    assert (detail.head, detail.base, detail.changed_files) == ("feature", "main", 2)


def test_pr_without_user() -> None:
    assert format_pr_summary(make_pr(user=None)).author is None


def make_file(patch: str | None) -> SimpleNamespace:
    return SimpleNamespace(
        filename="a.py", status="modified", additions=1, deletions=1, previous_filename=None, patch=patch
    )


def test_long_patch_is_cut_and_flagged() -> None:
    result = format_pr_file(make_file("x" * (MAX_PATCH_CHARS + 1)))
    assert len(result.patch) == MAX_PATCH_CHARS and result.patch_truncated


def test_short_and_missing_patch() -> None:
    assert format_pr_file(make_file("+a")).patch_truncated is False
    assert format_pr_file(make_file(None)).patch is None
