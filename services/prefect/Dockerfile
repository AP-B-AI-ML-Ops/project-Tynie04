FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /prefect

COPY requirements.txt .

RUN uv pip install -r requirements.txt --system

RUN prefect config set PREFECT_API_URL="http://127.0.0.1:4200/api"

CMD ["prefect", "server", "start", "--host", "0.0.0.0", "--port", "4200"]
