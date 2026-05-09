# Renewable Energy Forecasting

An end-to-end MLOps system that predicts daily solar energy production (in kWh) for the Antwerp region using weather forecast data.

## Problem Description

Grid operators and energy traders need reliable short-term forecasts of renewable energy production to make balancing decisions. Solar output is weather-dependent and hard to predict without a model.

This system predicts the total daily solar energy production (kWh) for Flanders based on incoming solar radiation forecasts. The input is the forecasted daily solar radiation (W/m²) from the Open Meteo ECMWF model, combined with time features (month, day of year). The output is the predicted solar production in kWh for that day.

Because Open Meteo provides radiation forecasts up to 16 days ahead, the deployed API can make real predictions using live forecast data, not just backtests.

## Architecture

The system consists of the following containerized services:

| Service | Description | Port |
|---|---|---|
| `database` | PostgreSQL backend for MLflow and monitoring | 5432 |
| `experiment-tracking` | MLflow server for experiment tracking and model registry | 5000 |
| `orchestration` | Prefect server for workflow scheduling | 4200 |
| `web-service` | REST API for on-demand solar production forecasts | 8000 |
| `batch-service` | Scheduled Prefect pipeline for inference and monitoring | - |
| `monitoring` | Evidently-based model performance monitoring | - |
| `grafana` | Dashboard for visualizing model metrics | 3000 |

## Data

The dataset comes from the Data Engineering course and combines:

- `sun_combined.csv` -- daily solar radiation (W/m²) from Open Meteo ECMWF, KMI, and Kaggle sources
- `productie_comnbined.csv` -- hourly solar and wind production (kWh) from Energie Vlaanderen and Elia

The training set is built by joining these on date and aggregating production to daily totals. This results in approximately 379 days of labeled data covering March 2025 to March 2026.

Place raw data files in `data/raw/` before running the training pipeline.

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python package manager)

### 1. Clone the repository

```bash
git clone <repo-url>
cd project-Tynie04
```

### 2. Configure environment variables

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

The defaults in `example.env` work out of the box for local development. Only change the database credentials if you need to.

### 3. Start the stack

```bash
docker compose up -d --build
```

This builds and starts all services. On first run, allow a minute for the database and Prefect server to initialize.

Verify everything is running:

```bash
docker compose ps
```

### 4. Access the services

- MLflow: http://localhost:5000
- Prefect: http://localhost:4200
- Grafana: http://localhost:3000
- Web API: http://localhost:8000

### Makefile shortcuts

A `Makefile` is provided for common tasks. It requires `make` to be installed (available by default on Mac and Linux):

```bash
make up        # start the stack
make down      # stop the stack
make build     # rebuild images
make logs      # stream logs from all services
make clean     # stop and remove all volumes
```

### Dev Container (optional)

If you use VS Code, a dev container is included that sets up the full development environment automatically. It comes with Python, uv, and all dependencies pre-installed. Open the project in VS Code, install the Dev Containers extension, and click "Reopen in Container" when prompted. The post-create command runs `make post-create` which installs dependencies and pre-commit hooks automatically.

This is useful if you do not want to install uv or Python locally.

## Local Development

Install dependencies locally using uv:

```bash
uv sync
```

This creates a `.venv` and installs all dependencies defined in `pyproject.toml`, including dev tools like ruff, mypy, and pytest.

### Pre-commit hooks

Install the hooks once after cloning:

```bash
uv run pre-commit install
```

From that point on, every `git commit` automatically runs:

- Ruff linting and formatting
- File checks (large files, merge conflicts, syntax errors, private keys)
- The pytest test suite

To run the hooks manually without committing:

```bash
uv run pre-commit run --all-files
```

To run tests manually:

```bash
uv run pytest tests/
```

## Services

### Web Service

`POST /predict` -- accepts a JSON body with radiation and date features, returns predicted solar production in kWh.

### Batch Service

A scheduled Prefect flow that fetches fresh Open Meteo radiation forecasts, runs inference using the latest registered model, stores predictions to the database, and compares them against Elia actuals.

### Monitoring

An Evidently-based Prefect flow that computes error metrics (RMSE) over time, visualizes them in Grafana, and triggers a retraining flow when a defined threshold is exceeded.
