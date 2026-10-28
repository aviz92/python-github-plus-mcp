# python-github-plus-mcp

An MCP server that lets any MCP client work with GitHub (github.com and GitHub Enterprise Server):
read repositories, branches, tags, pull requests, files and workflow runs, then optionally create branches,
tags and pull requests, comment, assign, approve, trigger workflows, merge and delete.

It is a thin layer over [python-github-plus](https://github.com/aviz92/python-github-plus), which does the GitHub
work (defaults, validation, paging, error handling). This package only defines the tools and shapes their
results for a model.

## Requirements

- [uv](https://docs.astral.sh/uv/) (it provides `uvx`, and installs Python 3.12+ if needed)
- git, to install straight from GitHub
- A GitHub [fine-grained personal access token](https://github.com/settings/personal-access-tokens/new)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # once, if uv is not installed
```

## Quick start

### Claude Desktop

Add the server to `claude_desktop_config.json`, then restart the app:

```json
{
  "mcpServers": {
    "github-plus": {
      "command": "/Users/you/.local/bin/uvx",
      "args": [
        "--from", "git+https://github.com/aviz92/python-github-plus-mcp@main",
        "python-github-plus-mcp"
      ],
      "env": {
        "GITHUB_ACCESS_TOKEN": "github_pat_..."
      }
    }
  }
}
```

- Use the full path to `uvx` (`which uvx` prints it). Claude Desktop does not load your shell's `PATH`.
- With `@main`, every restart of the app picks up the latest commit on `main`. To stay on one version,
  pin a tag instead, e.g. `@v0.1.0`.
- The token lives only in this local file. Never commit it.
- If you also run GitHub's official MCP server, give this one a different name (here `github-plus`).

### Claude Code

```bash
claude mcp add github-plus \
  -e GITHUB_ACCESS_TOKEN=github_pat_... \
  -e GITHUB_MCP_DEFAULT_REPO=your-user/your-repo \
  -- uvx --from git+https://github.com/aviz92/python-github-plus-mcp@main python-github-plus-mcp
```

## Token permissions

Give the token access only to the repositories the model should see, with these repository permissions:

| Permission | Read-only server | With writes | Used for |
|---|---|---|---|
| Metadata | Read | Read | Required for every token |
| Contents | Read | Read and write | Files, branches, tags; merging |
| Pull requests | Read | Read and write | Listing, creating, commenting, assigning, approving, merging |
| Actions | Read | Read and write | Workflows and runs; triggering a workflow |

A 403 from GitHub comes back as a tool error naming the permission the token is missing.

## Configuration

All settings are environment variables (or a `.env` file in the working directory; see `env.template`).
The credentials use the same names as python-github-plus, so one `.env` serves both.

| Variable | Default | Meaning |
|---|---|---|
| `GITHUB_ACCESS_TOKEN` | | Personal access token |
| `GITHUB_BASE_URL` | `https://api.github.com` | GitHub Enterprise Server API URL, e.g. `https://github.example.com/api/v3` |
| `GITHUB_MCP_DEFAULT_REPO` | | `owner/name` used when a tool call gives no `repo` |
| `GITHUB_MCP_READ_ONLY` | `true` | When `true`, write tools are not registered at all |
| `GITHUB_MCP_ENABLE_DESTRUCTIVE` | `false` | Register merge and delete tools (also needs `GITHUB_MCP_READ_ONLY=false`) |
| `GITHUB_MCP_MAX_RESULTS` | `100` | Upper bound for any `limit` |
| `GITHUB_MCP_MAX_FILE_CHARS` | `100000` | Longer file contents are cut and flagged `truncated` |
| `GITHUB_MCP_TRANSPORT` | `stdio` | `stdio` or `streamable-http` |
| `GITHUB_MCP_HOST` | `127.0.0.1` | HTTP transport only |
| `GITHUB_MCP_PORT` | `8000` | HTTP transport only |

## Tools

Every tool takes `repo` (`owner/name`), falling back to `GITHUB_MCP_DEFAULT_REPO`. All repositories share one
connection. List tools take `limit` and return `truncated: true` when more exist.

| Tool | Available | What it does |
|---|---|---|
| `github_get_repo` | always | Repository info, including the default branch |
| `github_list_branches` | always | Branches with their head sha |
| `github_list_tags` | always | Tags with the commit each points to |
| `github_list_pull_requests` | always | Pull requests by `state` (`open`, `closed`, `all`) and `base`; merged ones show state `merged` |
| `github_get_pull_request` | always | One pull request: description, mergeability, size, assignees, reviewers, labels |
| `github_get_pull_request_files` | always | Files a pull request changes, with their diff (long diffs are cut) |
| `github_get_file` | always | A text file's content at a branch, tag or sha (default branch if omitted) |
| `github_list_directory` | always | A directory's entries |
| `github_list_workflows` | always | Actions workflows with their id and file name |
| `github_list_workflow_runs` | always | Runs of a workflow (by name, file name or id), newest first |
| `github_get_workflow_run` | always | One run's status and conclusion |
| `github_create_branch` | writes enabled | Create a branch (from the default branch if omitted) |
| `github_create_pull_request` | writes enabled | Open a pull request, optionally as a draft |
| `github_comment_on_pull_request` | writes enabled | Add a comment |
| `github_assign_pull_request` | writes enabled | Add assignees |
| `github_approve_pull_request` | writes enabled | Submit an approving review |
| `github_close_pull_request` / `github_reopen_pull_request` | writes enabled | Close without merging, or reopen |
| `github_trigger_workflow` | writes enabled | Run a `workflow_dispatch` workflow; returns the run id when GitHub reports it |
| `github_create_tag` | writes enabled | Annotated tag on a sha or a branch head |
| `github_merge_pull_request` | destructive enabled | Merge, squash or rebase. Cannot be undone |
| `github_delete_branch` / `github_delete_tag` | destructive enabled | Delete a branch or tag. Cannot be undone |

### Enabling writes

Add to the server's `env`:

```json
"GITHUB_MCP_READ_ONLY": "false"
```

Merging and deleting have their own switch because they cannot be undone:

```json
"GITHUB_MCP_ENABLE_DESTRUCTIVE": "true"
```

## Access and safety

- **The server can do whatever the token can do.** Limit it with a fine-grained token that covers only the
  repositories and permissions you want; GitHub enforces it on every request.
- Read-only by default, and merge/delete need a second, explicit switch.
- Not exposed on purpose: repository settings, branch protection and collaborator management, and waiting on a
  workflow run (a tool that blocks for minutes; the model polls `github_get_workflow_run` instead).
- File writes are not exposed: commit through branches and pull requests.

## Docker and the HTTP transport (experimental)

```bash
docker build -t python-github-plus-mcp .
docker run -i --rm -e GITHUB_ACCESS_TOKEN -e GITHUB_MCP_DEFAULT_REPO python-github-plus-mcp
```

The image runs over stdio by default. `GITHUB_MCP_TRANSPORT=streamable-http` serves on
`GITHUB_MCP_HOST:GITHUB_MCP_PORT` instead; in Docker, set `GITHUB_MCP_HOST=0.0.0.0` and publish the port.

**The HTTP transport has no authentication.** Anyone who can reach the port acts with the configured token.
Bind to loopback, or put an authenticating reverse proxy in front.

## Development

```bash
git clone https://github.com/aviz92/python-github-plus-mcp
cd python-github-plus-mcp
uv sync --group dev
uv run pytest                 # mocked tests only
uv run pre-commit run --all-files
```

To run a client against your working copy, point it at the checkout:

```json
"command": "/Users/you/.local/bin/uv",
"args": ["--directory", "/path/to/python-github-plus-mcp", "run", "python-github-plus-mcp"]
```

### Integration tests

`uv run pytest -m integration` calls the tools through the server against the real GitHub API, with
`GITHUB_ACCESS_TOKEN` from the environment or `.env`, and needs a sandbox repository:

| Variable | Meaning |
|---|---|
| `GITHUB_TEST_REPO` | Sandbox repo (`owner/name`). The read tests use an open PR there if one exists; the write tests create temporary branches, a commit, pull requests and a tag, merge into a temporary branch, and delete everything. GitHub cannot delete pull requests, so each run leaves two closed ones. |

## License

MIT
