from unittest.mock import MagicMock, patch

from github_plus_mcp import __main__
from github_plus_mcp.settings import Transport
from tests.common import make_settings


def test_main_runs_with_configured_transport() -> None:
    server = MagicMock()
    settings = make_settings(github_mcp_transport=Transport.STREAMABLE_HTTP)
    with (
        patch.object(__main__, "create_server", return_value=server),
        patch.object(__main__, "get_settings", return_value=settings),
    ):
        __main__.main()
    server.run.assert_called_once_with(transport="streamable-http")
