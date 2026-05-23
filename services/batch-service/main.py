import math
import os
from datetime import UTC, datetime, timedelta

import mlflow
import mlflow.pyfunc
import pandas as pd
import requests
from prefect import flow, task
from sqlalchemy import create_engine, text

MLFLOW_TRACKING_URI = os.getenv(
    "MLFLOW_TRACKING_URI", "http://experiment-tracking:5000"
)
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_HOST = os.getenv("POSTGRES_CONTAINER_HOST", "database")
POSTGRES_DB = os.getenv("POSTGRES_MONITORING_DB", "monitoring_db")

# Antwerp (Stadspark) coordinates
LAT = 51.2117763328765
LON = 4.414811842605016

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)


def get_engine():
    return create_engine(
        f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}/{POSTGRES_DB}"
    )


def ensure_table():
    with get_engine().connect() as conn:
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS predictions (
                id              SERIAL PRIMARY KEY,
                tijd            TIMESTAMP WITH TIME ZONE,
                predicted_mw    FLOAT,
                actual_mw       FLOAT,
                radiation       FLOAT,
                model_version   TEXT,
                created_at      TIMESTAMP DEFAULT NOW()
            )
        """)
        )
        conn.commit()


@task(name="load-model")
def load_model():
    model = mlflow.pyfunc.load_model("models:/solar-forecast-model-hourly/latest")
    client = mlflow.tracking.MlflowClient()
    versions = client.search_model_versions("name='solar-forecast-model-hourly'")
    latest = sorted(versions, key=lambda v: int(v.version), reverse=True)[0]
    return model, latest.version


@task(name="fetch-radiation-forecast")
def fetch_radiation_forecast():
    # Use yesterday so radiation and Elia actuals are both fully available
    yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")

    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": LAT,
            "longitude": LON,
            "hourly": "shortwave_radiation",
            "start_date": yesterday,
            "end_date": yesterday,
            "timezone": "Europe/Brussels",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    df = pd.DataFrame(
        {
            "tijd": pd.to_datetime(data["hourly"]["time"]),
            "radiation": data["hourly"]["shortwave_radiation"],
        }
    )
    df["tijd"] = df["tijd"].dt.tz_localize("Europe/Brussels")
    print(f"Fetched {len(df)} hours of radiation for {yesterday}")
    return df


@task(name="fetch-elia-actuals")
def fetch_elia_actuals():
    now = datetime.now(UTC)
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    date_start = f"{yesterday}T00:00:00"
    date_end = f"{yesterday}T23:59:59"

    resp = requests.get(
        "https://opendata.elia.be/api/explore/v2.1/catalog/datasets/ods032/records",
        params={
            "limit": 100,
            "where": f"region='Flanders' AND datetime>='{date_start}' AND datetime<='{date_end}'",
            "order_by": "datetime asc",
        },
        timeout=30,
    )
    resp.raise_for_status()
    records = resp.json()["results"]

    if not records:
        print("No Elia actuals available")
        return pd.DataFrame(columns=["tijd", "actual_mw"])

    df = pd.DataFrame(
        [{"tijd": r["datetime"], "actual_mw": r["measured"]} for r in records]
    )
    df["tijd"] = pd.to_datetime(df["tijd"], utc=True)
    df = df.set_index("tijd").resample("1h").mean().reset_index()
    print(f"Fetched {len(df)} hours of Elia actuals for {yesterday}")
    return df


@task(name="run-predictions")
def run_predictions(model, df_radiation):
    def compute_features(row):
        dt = row["tijd"]
        doy = dt.timetuple().tm_yday
        return {
            "open_meteo_radiation": row["radiation"],
            "month": dt.month,
            "sin_day": math.sin(2 * math.pi * doy / 365),
            "cos_day": math.cos(2 * math.pi * doy / 365),
            "sin_hour": math.sin(2 * math.pi * dt.hour / 24),
            "cos_hour": math.cos(2 * math.pi * dt.hour / 24),
        }

    features = pd.DataFrame(
        [compute_features(row) for _, row in df_radiation.iterrows()]
    )
    predictions = model.predict(features)

    # Model outputs kWh, convert to MW for comparison with Elia (divide by 1000)
    df_radiation = df_radiation.copy()
    df_radiation["predicted_mw"] = predictions / 1000
    return df_radiation


@task(name="save-predictions")
def save_predictions(df_predictions, df_actuals, model_version):
    ensure_table()

    df_predictions["tijd"] = pd.to_datetime(df_predictions["tijd"]).dt.tz_convert("UTC")

    if not df_actuals.empty:
        df_actuals["tijd"] = pd.to_datetime(df_actuals["tijd"]).dt.tz_convert("UTC")
        merged = df_predictions.merge(df_actuals, on="tijd", how="left")
    else:
        merged = df_predictions.copy()
        merged["actual_mw"] = None

    rows = merged[["tijd", "predicted_mw", "actual_mw", "radiation"]].copy()
    rows["model_version"] = model_version
    rows.to_sql("predictions", get_engine(), if_exists="append", index=False)
    print(f"Saved {len(rows)} predictions to monitoring_db")


@flow(name="batch-forecast")
def batch_forecast():
    model, model_version = load_model()
    df_radiation = fetch_radiation_forecast()
    df_actuals = fetch_elia_actuals()
    df_predictions = run_predictions(model, df_radiation)
    save_predictions(df_predictions, df_actuals, model_version)
    print(f"Batch run complete: model v{model_version}")


if __name__ == "__main__":
    batch_forecast.serve(
        name="batch-forecast",
        cron="0 6 * * *",
    )
