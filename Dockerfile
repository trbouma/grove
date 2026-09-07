# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder

ARG POETRY_VERSION=1.8.2

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1

RUN apt-get update \
    && apt-get install --yes --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install "poetry==${POETRY_VERSION}"

WORKDIR /app

COPY pyproject.toml poetry.lock README.md LICENSE /app/
COPY grove /app/grove
RUN poetry install --only main --no-ansi


FROM python:3.12-slim AS runtime

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GROVE_DATA_DIR=/data

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system grove \
    && adduser --system --ingroup grove grove \
    && install -d -o grove -g grove /app /data

WORKDIR /app

COPY --from=builder --chown=grove:grove /app/.venv /app/.venv
COPY --from=builder --chown=grove:grove /app/grove /app/grove

USER grove

EXPOSE 8000
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["uvicorn", "grove.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
