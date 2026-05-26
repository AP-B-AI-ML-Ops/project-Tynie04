# Renewable Energy Forecasting

An end-to-end MLOps system that predicts solar energy production for Flanders using weather forecast data, at daily or hourly granularity.

## Problem Description

Grid operators and energy traders need reliable short-term forecasts of renewable energy production to make balancing decisions. Solar output is weather-dependent and hard to predict without a model.

This system trains two `RandomForestRegressor` models (daily and hourly granularity) using solar radiation forecasts from Open Meteo (ECMWF) combined with cyclical time features. The output is the predicted total solar production in kWh for Flanders for the requested datetime.

**Inputs:** shortwave radiation (W/m²), month, cyclical day-of-year encoding (sin/cos), and for hourly predictions, cyclical hour-of-day encoding (sin/cos).

**Output:** predicted solar production in kWh for Flanders.

Because Open Meteo provides radiation forecasts up to 16 days ahead, the deployed API can make real predictions using live forecast data, not just backtests.

## Project Structure

The project is fully containerized using Docker Compose. Each concern is isolated in its own service:

- **database**: PostgreSQL backend shared by MLflow, Prefect, and the monitoring pipeline (port 5432)
- **experiment-tracking**: MLflow server for experiment tracking and the model registry (port 5000)
- **orchestration**: Prefect server for scheduling and observing all flows (port 4200)
- **training-service**: Prefect flow that preprocesses data, runs hyperparameter optimization with Optuna, and registers the best model in MLflow
- **web-service**: Flask REST API for on-demand solar production forecasts (port 8000)
- **batch-service**: Prefect flow that runs daily inference and stores predictions with Elia actuals
- **monitoring**: Prefect flow that computes Evidently metrics and triggers retraining when thresholds are exceeded
- **grafana**: Dashboard for visualizing model performance over time (port 3000)

Source code for the training pipeline lives in `src/`. Each deployed service has its own directory under `services/` with a `Dockerfile` and `requirements.txt`.

## Data

The raw data files are **not included in this repository** and must be placed manually before training.

### Required files

Place the following files in `data/raw/`:

| File | Description | Expected columns |
|---|---|---|
| `sun_combined.csv` | Daily solar radiation from Open Meteo ECMWF, KMI, and Kaggle sources | `id`, `datum`, `open_meteo_radiation`, `kmi_radiation_avg`, `kaggle_radiation_avg` |
| `productie_comnbined.csv` | Hourly solar and wind production (kWh) from Energie Vlaanderen and Elia | `tijd`, `vlaanderen zon kwh`, `vlaanderen wind kwh`, `elia zon kwh`, `elia wind kwh` |

The directory structure must be:

```
data/
└── raw/
    ├── sun_combined.csv
    └── productie_comnbined.csv
```

The `data/processed/` directory is created automatically by the training pipeline.

> These files originate from the Data Engineering course. If you do not have access to them, contact your instructor.

### What the training pipeline uses

- `sun_combined.csv`: the `datum` and `open_meteo_radiation` columns are used as the radiation feature.
- `productie_comnbined.csv`: the `tijd` and `elia zon kwh` columns are used as the production target.

Two datasets are built from this:

- **Daily**: ~379 rows, one row per day with aggregated production
- **Hourly**: ~9073 rows, one row per hour with hourly production

## Model

Two `RandomForestRegressor` models are trained and registered in MLflow:

| Model | Features | Approx. RMSE |
|---|---|---|
| `solar-forecast-model-daily` | radiation, month, sin/cos day-of-year | ~3M kWh |
| `solar-forecast-model-hourly` | radiation, month, sin/cos day-of-year, sin/cos hour | ~320K kWh |

Cyclical encoding (sin/cos) is used for day-of-year and hour so the model understands that day 365 and day 1 are adjacent, and that hour 23 and hour 0 are adjacent. Hyperparameters are tuned with Optuna (20 trials per model). The best model from HPO is registered in the MLflow model registry.

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

For local development (optional, only needed if you want to run services outside of Docker):
- [uv](https://docs.astral.sh/uv/getting-started/installation/), used as the Python package manager across all services and local development

> **Dev Container:** If you use VS Code, a dev container is included that sets up the full development environment automatically with Python, uv, and all dependencies pre-installed. Install the Dev Containers extension and click "Reopen in Container" when prompted. The dev container uses the same `docker-compose.yml` as the full stack, so all services (MLflow, Prefect, web service, etc.) are started automatically alongside the dev environment. The post-create command installs dependencies and pre-commit hooks automatically, so no additional setup is needed.

### 1. Clone the repository

```bash
git clone https://github.com/AP-B-AI-ML-Ops/project-Tynie04
cd project-Tynie04
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

The defaults in `.env.example` work out of the box for local development. The key variables are database credentials, MLflow tracking URI, and the Prefect API URL, all pre-configured for the Docker network.

> **Note:** If you are using the dev container, this step is handled automatically. On startup, `.env` is created from `.env.example` if it does not already exist. If a `.env` file is already present, it is left untouched. This generated `.env` uses the same defaults as `.env.example`, which are compatible with the Docker Compose setup. If you need to customize any environment variables, you can edit the `.env` file after the dev container has started, or you can make an `.env` file locally before starting the dev container since the dev container will not overwrite an existing `.env`.

### 3. Start the stack

```bash
docker compose up -d --build
```

This builds and starts all services. On first run, allow a minute for the database and Prefect server to initialize before the other services come up.

```bash
docker compose ps  # verify all services are running
```

### 4. Access the services

| Service | URL |
|---|---|
| MLflow | http://localhost:5000 |
| Prefect | http://localhost:4200 |
| Grafana | http://localhost:3000 |
| Web API | http://localhost:8000 |

### 5. Train the models

On startup, the training service registers a Prefect deployment called `solar-forecast-training`. Trigger it from the Prefect UI at http://localhost:4200, or run it directly:

```bash
docker compose run --rm training-service python -m src.main
```

This trains both the daily and hourly models and registers them in MLflow.

## Local Development 
### _(Not necessary if using the dev container)_

Install dependencies locally using uv:

```bash
uv sync
```

This creates a `.venv` and installs all dependencies defined in `pyproject.toml`, including dev tools like ruff and pytest.

### Pre-commit hooks

Every commit automatically runs a set of checks via pre-commit. Install the hooks once after cloning:

```bash
uv run pre-commit install
```

The hooks run on every `git commit`:

- **Ruff**: linting and formatting
- **File checks**: large files, merge conflicts, syntax errors, private keys
- **pytest**: the full test suite must pass before a commit is accepted

To run manually without committing:

```bash
uv run pre-commit run --all-files
uv run pytest tests/
```

## Services

### Web Service

`POST /predict`: accepts a datetime and radiation value, returns predicted solar production.

**Hourly prediction (Linux/Mac):**

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"granularity": "hourly", "datetime": "2024-06-21T14:00:00", "open_meteo_radiation": 650.0}'
```

**Hourly prediction (Windows PowerShell):**

```powershell
Invoke-WebRequest -Uri http://localhost:8000/predict -Method POST `
  -ContentType "application/json" `
  -Body '{"granularity": "hourly", "datetime": "2024-06-21T14:00:00", "open_meteo_radiation": 650.0}'
```

**Response:**

```json
{
  "datetime": "2024-06-21T14:00:00",
  "granularity": "hourly",
  "predicted_zon_kwh": 18423.5
}
```

---

**Daily prediction (Linux/Mac):**

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"granularity": "daily", "datetime": "2024-06-21", "open_meteo_radiation": 180.5}'
```

**Daily prediction (Windows PowerShell):**

```powershell
Invoke-WebRequest -Uri http://localhost:8000/predict -Method POST `
  -ContentType "application/json" `
  -Body '{"granularity": "daily", "datetime": "2024-06-21", "open_meteo_radiation": 180.5}'
```

**Response:**

```json
{
  "datetime": "2024-06-21T00:00:00",
  "granularity": "daily",
  "predicted_zon_kwh": 23104490.86
}
```

`GET /health`: returns `{"status": "ok"}`. Models are loaded lazily and cached.

### Batch Service

A Prefect flow scheduled daily at 06:00 that fetches yesterday's hourly solar radiation from the Open Meteo API, runs inference using the latest registered model, and stores predictions alongside Elia actuals in the `monitoring_db` database. Predictions are stored in MW (model output in kWh divided by 1000) to match Elia actuals.

The flow can also be triggered manually from the Prefect UI at http://localhost:4200. At least one successful run is required before the Grafana dashboard can display any data.

### Monitoring

A Prefect flow scheduled daily at 02:00 that loads the last 720 hours of predictions with actuals, runs an Evidently regression report (RMSE, MAE, mean error), and stores the results to the `monitoring_metrics` table. If RMSE exceeds the configured threshold, it automatically triggers the `solar-forecast-training` retraining deployment via the Prefect API. The threshold is controlled by the `RMSE_THRESHOLD_MW` variable in `.env` (default: 2000 MW).

The flow can also be triggered manually from the Prefect UI at http://localhost:4200. At least one successful run is required before the RMSE/MAE panels in Grafana have data to display.

### Grafana

The Grafana dashboard at http://localhost:3000 shows predictions vs actuals, prediction error over time, and RMSE/MAE trends. The dashboard was created in Grafana and exported to JSON, which is mounted into the container at startup via the provisioning configuration in `monitoring/grafana/provisioning/`. This means the dashboard is always available without any manual import steps.

## Dependencies

All service dependencies are pinned in the respective `requirements.txt` files under `services/`. The training pipeline dependencies are managed via `pyproject.toml` at the project root. The project uses Python 3.12 across all services.
