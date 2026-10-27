from collections.abc import Callable, Sequence
from typing import Annotated, Any, TypeVar

from pydantic import Field

T = TypeVar("T")

Repo = Annotated[
    str | None, Field(description="Repository as 'owner/name'. Defaults to GITHUB_MCP_DEFAULT_REPO when omitted.")
]
Ref = Annotated[str | None, Field(description="Branch, tag or commit sha. Defaults to the repo's default branch.")]


def clamp(limit: int, max_results: int) -> int:
    return min(max(limit, 1), max_results)


def paginate(found: Sequence[Any], limit: int, fmt: Callable[[Any], T]) -> dict[str, Any]:
    """`found` holds up to limit + 1 items; the extra one only tells whether more exist."""
    items = [fmt(item) for item in found[:limit]]
    return {"items": items, "returned": len(items), "truncated": len(found) > limit}
