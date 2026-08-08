FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GROVE_DATA_DIR=/data

WORKDIR /app

RUN addgroup --system grove && adduser --system --ingroup grove grove

COPY pyproject.toml README.md LICENSE /app/
COPY grove /app/grove
RUN pip install --no-cache-dir . && \
    mkdir -p /data && \
    chown -R grove:grove /data /app

USER grove

EXPOSE 8000
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["uvicorn", "grove.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
