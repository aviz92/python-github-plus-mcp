from mcp.server.fastmcp import FastMCP

from github_plus_mcp.client import RepoClients
from github_plus_mcp.settings import Settings
from github_plus_mcp.tools.read import register_read_tools
from github_plus_mcp.tools.write import register_destructive_tools, register_write_tools


def register_tools(mcp: FastMCP, settings: Settings) -> None:
    """Register tools by mode. Tools that are off are not registered, so the model never sees them."""
    clients = RepoClients(settings)
    register_read_tools(mcp, settings, clients)
    if settings.github_mcp_read_only:
        return
    register_write_tools(mcp, clients)
    if settings.github_mcp_enable_destructive:
        register_destructive_tools(mcp, clients)
