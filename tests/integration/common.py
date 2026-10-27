import os

import pytest
from dotenv import load_dotenv

from github_plus_mcp.settings import Settings

load_dotenv()

TEST_REPO = os.environ.get("GITHUB_TEST_REPO", "")

requires_test_repo = pytest.mark.skipif(
    not (os.environ.get("GITHUB_ACCESS_TOKEN") and TEST_REPO),
    reason="GITHUB_ACCESS_TOKEN and GITHUB_TEST_REPO (a sandbox repo) are required",
)


def live_settings(**overrides: object) -> Settings:
    """Real credentials from the environment, the sandbox as default repo, no local .env for MCP flags."""
    return Settings(_env_file=None, github_mcp_default_repo=TEST_REPO, **overrides)
