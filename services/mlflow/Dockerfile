FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY requirements.txt .

RUN uv pip install -r requirements.txt --system

CMD ["sh", "-c", "mlflow server \
     --host 0.0.0.0 \
     --port 5000 \
     --backend-store-uri postgresql+psycopg2://${POSTGRES_USER}:${POSTGRES_PASSWORD}@database/mlflow_db \
     --default-artifact-root /mlflow-artifacts \
     --serve-artifacts \
     --allowed-hosts '*'"]
