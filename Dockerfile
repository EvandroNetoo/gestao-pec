# Stage 1: build com uv
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS python-builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/code/.venv

WORKDIR /code

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-install-project --no-dev

ADD . /code

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


# Stage final
FROM python:3.14-slim-bookworm

ENV PATH="/code/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y curl libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code

COPY --from=python-builder /code /code

RUN mkdir -p data media logs src/staticfiles

COPY start.sh /start
RUN chmod +x /start

CMD ["/start"]
