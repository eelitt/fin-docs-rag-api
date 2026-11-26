FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src src
COPY prompts prompts
ENV PYTHONPATH=/app/src
ENV PATH="/app/.venv/bin:$PATH"
ENV HOME=/tmp
EXPOSE 8000
USER nobody
CMD ["uvicorn", "fin_docs_rag.http.serve:app", "--host", "0.0.0.0", "--port", "8000"]
