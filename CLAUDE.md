# CLAUDE.md

## Plan Mode Rules

1. Every plan includes a pre-commit step.
2. List every file to be created or modified.
3. Run `pre-commit run --files <changed_files>` before any commit.
4. If pre-commit fails, add a fix step before retrying.
5. Never mark a plan complete until pre-commit passes.
6. Include rollback steps for multi-file changes.

## Project rules

- The MCP is a thin layer over [python-github-plus](https://github.com/aviz92/python-github-plus).
  If any Python caller would want a change, it belongs in the library; only code that exists because an LLM
  is the caller (tool definitions, result shaping, limits and truncation) belongs here.
- Never print to stdout in the server: with the stdio transport, stdout is the protocol channel.
