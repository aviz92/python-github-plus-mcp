from mcp.server.fastmcp import FastMCP

from github_plus_mcp.settings import Settings, get_settings
from github_plus_mcp.tools import register_tools

INSTRUCTIONS = (
    "GitHub tools. Every tool takes `repo` as 'owner/name'{default}. "
    "List results carry `truncated: true` when more exist than `limit`."
)


def create_server(settings: Settings | None = None) -> FastMCP:
    settings = settings or get_settings()
    default = settings.github_mcp_default_repo
    mcp = FastMCP(
        name="github-plus",
        instructions=INSTRUCTIONS.format(default=f"; it defaults to {default}" if default else ""),
        host=settings.github_mcp_host,
        port=settings.github_mcp_port,
    )
    register_tools(mcp, settings)
    return mcp
