FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY . /app
WORKDIR /app

RUN uv pip install -r requirements.txt --system

RUN prefect config set PREFECT_API_URL=http://orchestration:4200/api

EXPOSE 8000

CMD ["python", "main.py"]
