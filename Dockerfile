FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY . .

RUN uv python pin 3.14
RUN uv sync --no-dev

ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:${PATH}"
CMD ["uv", "run", "olliebot"]
