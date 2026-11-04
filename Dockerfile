# Official registry manifest verified by SHA-256 on 2026-11-04.
FROM python:3.13.17-slim-bookworm@sha256:e32be0e55814a08977501ca863271d9bd02443710db8f2afaf8372e2c4508530 AS runtime
LABEL org.opencontainers.image.title="Escrituracao contabil local (prototipo)" \
      org.opencontainers.image.source="https://github.com/codisplanfiscalai/escrituracao-contabil" \
      org.opencontainers.image.description="Loopback-only, single-user prototype; no public service or homologated exporter"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/data
WORKDIR /app
COPY src/ src/
COPY config/ config/
COPY packaging/launcher.py packaging/smoke_test.py packaging/
COPY pyproject.toml ./
RUN mkdir /data && chown 10001:10001 /data && chmod 700 /data \
    && chmod -R a+rX /app
USER 10001:10001
# No EXPOSE: no ports may be published. HTTP remains 127.0.0.1 inside its namespace.
ENTRYPOINT ["python", "packaging/launcher.py"]
CMD ["--database", "/data/accounting.sqlite3", "--port", "8765"]

FROM runtime AS test
COPY --chown=10001:10001 tests/ tests/
RUN python -m unittest discover -s tests -v
RUN python packaging/smoke_test.py

FROM runtime AS final
