from datetime import UTC, datetime, timezone
from types import SimpleNamespace
from typing import Any

from github_plus_mcp.settings import Settings

WRITABLE = {"github_mcp_read_only": False}
DESTRUCTIVE = {"github_mcp_read_only": False, "github_mcp_enable_destructive": True}
WHEN = datetime(2026, 10, 27, tzinfo=UTC)


def make_settings(**overrides: Any) -> Settings:
    """Settings that ignore any local .env, with a token and a default repo."""
    values = {"github_access_token": "t", "github_mcp_default_repo": "owner/default"} | overrides
    return Settings(_env_file=None, **values)


def user(login: str) -> SimpleNamespace:
    return SimpleNamespace(login=login)


def make_pr(number: int = 1, **overrides: Any) -> SimpleNamespace:
    """A pull request as PyGithub returns it, with list-payload and detail fields."""
    values = {
        "number": number,
        "title": f"PR {number}",
        "state": "open",
        "merged_at": None,
        "draft": False,
        "user": user("author"),
        "head": SimpleNamespace(ref="feature"),
        "base": SimpleNamespace(ref="main"),
        "updated_at": WHEN,
        "html_url": f"https://github.com/owner/default/pull/{number}",
        "body": "why",
        "created_at": WHEN,
        "mergeable": True,
        "mergeable_state": "clean",
        "commits": 2,
        "additions": 10,
        "deletions": 3,
        "changed_files": 2,
        "assignees": [user("a")],
        "requested_reviewers": [user("r")],
        "labels": [SimpleNamespace(name="bug")],
    }
    return SimpleNamespace(**(values | overrides))
