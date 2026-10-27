from threading import Lock

from python_github_plus import GitHubClient

from github_plus_mcp.settings import Settings


class RepoClients:
    """
    One GitHubClient per repository, created on first use. The first one opens the connection and the rest
    share it through `for_repo`, so a bad token fails the tool call, not the server start.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._clients: dict[str, GitHubClient] = {}
        self._lock = Lock()  # tools run in worker threads

    def get(self, repo: str | None = None) -> GitHubClient:
        if not (name := (repo or self._settings.github_mcp_default_repo).strip()):
            raise ValueError("No repo given and GITHUB_MCP_DEFAULT_REPO is not set: pass repo as 'owner/name'")
        key = name.lower()
        with self._lock:
            if key not in self._clients:
                self._clients[key] = self._create(name)
            return self._clients[key]

    def _create(self, name: str) -> GitHubClient:
        if self._clients:
            return next(iter(self._clients.values())).for_repo(name)
        # empty values fall back to the library's own env/.env handling and its "token required" error
        return GitHubClient(
            name,
            access_token=self._settings.github_access_token.get_secret_value() or None,
            base_url=self._settings.github_base_url or None,
        )
