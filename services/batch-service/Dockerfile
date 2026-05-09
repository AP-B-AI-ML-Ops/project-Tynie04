FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY . /

RUN uv pip install -r /requirements.txt --system

RUN prefect config set PREFECT_API_URL=http://orchestration:4200/api

RUN chmod +x /startPoolWorkers.sh

CMD ["/startPoolWorkers.sh"]
