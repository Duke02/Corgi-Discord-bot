FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin

WORKDIR /app

RUN mkdir /app/logs
RUN mkdir /app/db

COPY uv.lock .
COPY pyproject.toml . 

ENV UV_COMPILE_BYTECODE=1
ENV UV_HTTP_TIMEOUT=1000
RUN uv sync --native-tls

COPY corgi-bot/main.py .
COPY corgi-bot/playlist_manager.py .
COPY corgi-bot/database.py .
COPY corgi-bot/data_manager.py .
COPY .env .
CMD ["uv", "run", "--native-tls", "python", "-m", "main"]
