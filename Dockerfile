# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV POETRY_VERSION=1.8.3 \
    POETRY_VIRTUALENVS_CREATE=true \
    POETRY_NO_INTERACTION=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

# системные зависимости при необходимости расширь (gcc, libpq-dev и т.п.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential && \
    pip install --no-cache-dir "poetry==${POETRY_VERSION}" && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1) зависимости — сначала метаданные для кеша
COPY pyproject.toml poetry.lock* poetry.toml* /app/
RUN poetry install --no-root --only main

# 2) код
COPY src /app/src
COPY README.md /app/README.md

# порт не открываем — боту не нужен
CMD ["poetry", "run", "python", "-m", "tgbot.main"]
