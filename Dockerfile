# Official registry manifest verified by SHA-256 on 2026-11-04.
ARG PYTHON_IMAGE=docker.io/library/python:3.13.17-slim-bookworm@sha256:e32be0e55814a08977501ca863271d9bd02443710db8f2afaf8372e2c4508530
FROM ${PYTHON_IMAGE} AS runtime
LABEL org.opencontainers.image.title="Escritura - portal corporativo" \
      org.opencontainers.image.source="https://github.com/codisplanfiscalai/escrituracao-contabil" \
      org.opencontainers.image.description="Authenticated portal with scoped accounting services"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/data
ARG APP_VERSION=0.3.0
ENV ESCRITURA_VERSION=${APP_VERSION}
WORKDIR /app
COPY requirements-server.txt ./
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    python -m pip install --no-cache-dir --only-binary=:all: --require-hashes -r requirements-server.txt
COPY src/ src/
COPY config/ config/
COPY packaging/launcher.py packaging/smoke_test.py packaging/
COPY pyproject.toml VERSION ./
RUN mkdir /data && chown 10001:10001 /data && chmod 700 /data \
    && chmod -R a+rX /app
USER 10001:10001
EXPOSE 8765
ENTRYPOINT ["python", "-m", "src.server.runtime"]
CMD []

FROM runtime AS test
COPY --chown=10001:10001 tests/ tests/
RUN python -m unittest discover -s tests -v
RUN python packaging/smoke_test.py --server

FROM runtime AS final
