# Renewable Energy Forecasting

An end-to-end MLOps system that predicts solar energy production (in kWh) for Flanders using weather forecast data, at daily or hourly granularity.

## Problem Description

Grid operators and energy traders need reliable short-term forecasts of renewable energy production to make balancing decisions. Solar output is weather-dependent and hard to predict without a model.

This system trains two models (daily and hourly granularity) using solar radiation forecasts from Open Meteo (ECMWF) combined with cyclical time features. The output is the predicted total solar production in kWh for Flanders for the requested datetime.

Because Open Meteo provides radiation forecasts up to 16 days ahead, the deployed API can make real predictions using live forecast data, not just backtests.

## Architecture

The system consists of the following containerized services:

| Service | Description | Port |
|---|---|---|
| `database` | PostgreSQL backend for MLflow and Prefect | 5432 |
| `experiment-tracking` | MLflow server for experiment tracking and model registry | 5000 |
| `orchestration` | Prefect server for workflow scheduling | 4200 |
| `web-service` | REST API for on-demand solar production forecasts | 8000 |
| `batch-service` | Scheduled Prefect pipeline for inference and monitoring | - |
| `monitoring` | Evidently-based model performance monitoring | - |
| `grafana` | Dashboard for visualizing model metrics | 3000 |

## Data

The dataset comes from the Data Engineering course and combines:

- `sun_combined.csv`: daily solar radiation (W/m²) from Open Meteo ECMWF, KMI, and Kaggle sources
- `productie_comnbined.csv`: hourly solar and wind production (kWh) from Energie Vlaanderen and Elia

Two datasets are built from this:

- **Daily**: ~379 rows, one row per day with aggregated production
- **Hourly**: ~9073 rows, one row per hour with hourly production

Place raw data files in `data/raw/` before running the training pipeline.

## Model

Two `RandomForestRegressor` models are trained and registered in MLflow:

| Model | Features | Approx. RMSE |
|---|---|---|
| `solar-forecast-model-daily` | radiation, month, sin/cos day-of-year | ~3M kWh |
| `solar-forecast-model-hourly` | radiation, month, sin/cos day-of-year, sin/cos hour | ~320K kWh |

Cyclical encoding (sin/cos) is used for day-of-year and hour so the model understands that day 365 and day 1 are adjacent. Hyperparameters are tuned with Optuna (20 trials per model). The best model from HPO is registered in the MLflow model registry under the name `solar-forecast-model-{granularity}`.

The training pipeline runs as a Prefect flow and can be triggered from the Prefect UI at http://localhost:4200.

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

`POST /predict`: accepts a datetime and radiation value, returns predicted solar production in kWh. The service computes all cyclical features internally.

**Request:**

```json
{
  "granularity": "daily",
  "datetime": "2024-06-21",
  "open_meteo_radiation": 180.5
}
```

For hourly predictions, pass `"granularity": "hourly"` and a full datetime string:

```json
{
  "granularity": "hourly",
  "datetime": "2024-06-21T14:00:00",
  "open_meteo_radiation": 180.5
}
```

**Response:**

```json
{
  "datetime": "2024-06-21T00:00:00",
  "granularity": "daily",
  "predicted_zon_kwh": 23104490.86
}
```

`GET /health`: returns `{"status": "ok"}`.

Models are loaded lazily on first request and cached for subsequent calls.

### Batch Service

A scheduled Prefect flow that fetches fresh Open Meteo radiation forecasts, runs inference using the latest registered model, stores predictions to the database, and compares them against Elia actuals.

### Monitoring

An Evidently-based Prefect flow that computes error metrics (RMSE) over time, visualizes them in Grafana, and triggers a retraining flow when a defined threshold is exceeded.
