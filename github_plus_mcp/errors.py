from collections.abc import Callable
from functools import partial, wraps
from typing import Any

import anyio.to_thread
from github import GithubException
from mcp.server.fastmcp.exceptions import ToolError


def _github_message(err: GithubException) -> str:
    """GitHub's own message, its validation details, and for 403s the permission it wants."""
    data = err.data if isinstance(err.data, dict) else {}
    parts = [str(data.get("message") or err.data or "no message")]
    details = [e.get("message") or e.get("code") for e in data.get("errors") or [] if isinstance(e, dict)]
    parts += [str(d) for d in details if d]
    headers = {k.lower(): v for k, v in (err.headers or {}).items()}
    if err.status == 403 and (needed := headers.get("x-accepted-github-permissions")):
        parts.append(f"the token needs: {needed}")
    if err.status == 404:
        parts.append("check the repo, number, ref or path, and that the token can access the repo")
    return "; ".join(parts)


def to_tool_error(err: Exception) -> ToolError:
    """Map library/GitHub exceptions to a message the model can act on."""
    if isinstance(err, ToolError):
        return err
    if isinstance(err, GithubException):
        return ToolError(f"GitHub error {err.status}: {_github_message(err)}")
    if isinstance(err, ValueError):  # python-github-plus validation, missing token, bad repo name
        return ToolError(str(err))
    return ToolError(f"Unexpected error: {type(err).__name__}: {err}")


def tool_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Run a blocking tool in a worker thread and convert any exception into a ToolError.

    python-github-plus is synchronous; FastMCP runs sync tools on the event loop,
    which would stall every client of a streamable-http server.
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await anyio.to_thread.run_sync(partial(func, *args, **kwargs))
        except Exception as err:
            raise to_tool_error(err) from err

    return wrapper
