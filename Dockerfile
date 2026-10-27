FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock README.md ./
COPY github_plus_mcp/ ./github_plus_mcp/
RUN uv sync --frozen --no-dev

# stdio by default; set GITHUB_MCP_TRANSPORT=streamable-http to serve over HTTP
CMD ["uv", "run", "--no-sync", "python-github-plus-mcp"]
