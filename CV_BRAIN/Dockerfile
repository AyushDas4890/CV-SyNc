FROM python:3.11-slim

WORKDIR /app

# Dependencies are installed with pip into an explicit venv rather than with
# `uv sync`.
#
# Why: behind a TLS-inspecting corporate proxy (Sophos/Zscaler) uv cannot fetch
# from PyPI — it fails with "invalid peer certificate: UnknownIssuer" even with
# UV_SYSTEM_CERTS=1, because the proxy's CA is not in the image's trust store.
# pip's --trusted-host does work there, which is why the previous Dockerfile's
# pip step (installing uv) succeeded while `uv sync` failed. Using pip for the
# dependencies too makes the image buildable on that network.
#
# The runtime contract is unchanged: a self-contained /app/.venv, invoked
# directly, with no network access at container start.
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt ./

RUN python -m venv .venv \
    && .venv/bin/pip install \
        --trusted-host pypi.org \
        --trusted-host files.pythonhosted.org \
        --trusted-host pypi.python.org \
        -r requirements.txt

COPY . .

EXPOSE 8000

# Direct venv invocation — no resolver, no network at startup.
CMD [".venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
