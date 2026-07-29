FROM python:3.11-slim

WORKDIR /app

# UV_SYSTEM_CERTS=1 forces uv to use OpenSSL + system CA certs instead of
# its bundled rustls, which rejects corporate SSL-inspection proxy certs.
# UV_PYTHON pins uv to system Python, overriding .python-version (which says 3.10).
ENV UV_SYSTEM_CERTS=1
ENV UV_PYTHON=python3.11

RUN pip install --no-cache-dir \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    uv

COPY pyproject.toml uv.lock ./
# NOT --frozen: pyproject.toml gained `pypdf` (needed to measure whether the
# generated CV lands on 1 or 2 pages) and uv.lock has not been regenerated,
# so --frozen would fail the build with "the lockfile is not up-to-date".
# Plain `uv sync` re-resolves and refreshes the lock inside the image.
# Regenerate uv.lock locally with `uv lock` and restore --frozen when
# convenient — this only relaxes BUILD-time resolution; runtime is still the
# hermetic `.venv/bin/uvicorn` invocation below.
RUN uv sync --no-dev

COPY . .

EXPOSE 8000

# Use the pre-built venv's uvicorn directly — avoids any uv runtime network calls
CMD [".venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
