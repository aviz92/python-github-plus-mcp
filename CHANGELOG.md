# Changelog

## 0.1.0

### Added
- MCP server over python-github-plus 2.x: repository, branches, tags, pull requests and their files,
  file contents and directories, workflows and runs.
- Write tools (`GITHUB_MCP_READ_ONLY=false`): create branch, tag and pull request; comment, assign, approve,
  close and reopen pull requests; trigger workflows.
- Destructive tools (`GITHUB_MCP_ENABLE_DESTRUCTIVE=true`): merge pull requests, delete branches and tags.
- Multi-repo: every tool takes `repo` (`owner/name`), with `GITHUB_MCP_DEFAULT_REPO` as fallback;
  all repos share one connection.
- stdio and streamable-http transports, Dockerfile.
