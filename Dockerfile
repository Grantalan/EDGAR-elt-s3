# The daily pipeline, served by Prefect. docker-compose.yml runs it next to
# RustFS, ClickHouse and the Prefect server, so nothing depends on an open terminal.
FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev

CMD ["uv", "run", "--no-sync", "python", "-m", "edgar_etl_s3.pipeline.flow", "serve"]
