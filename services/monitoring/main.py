import os

import pandas as pd
import requests
from evidently import DataDefinition, Dataset, Regression, Report
from evidently.metrics import MAE, RMSE, MeanError
from evidently.presets import RegressionPreset
from prefect import flow, task
from sqlalchemy import create_engine, text

POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_HOST = os.getenv("POSTGRES_CONTAINER_HOST", "database")
POSTGRES_DB = os.getenv("POSTGRES_MONITORING_DB", "monitoring_db")
PREFECT_API_URL = os.getenv("PREFECT_API_URL", "http://orchestration:4200/api")
RMSE_THRESHOLD_MW = float(os.getenv("RMSE_THRESHOLD_MW", "2000.0"))


def get_engine():
    return create_engine(
        f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}/{POSTGRES_DB}"
    )


def ensure_metrics_table():
    with get_engine().connect() as conn:
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS monitoring_metrics (
                id          SERIAL PRIMARY KEY,
                run_date    DATE NOT NULL,
                rmse        FLOAT,
                mae         FLOAT,
                me          FLOAT,
                row_count   INTEGER,
                created_at  TIMESTAMP DEFAULT NOW()
            )
        """)
        )
        conn.commit()


@task(name="load-predictions")
def load_predictions():
    query = """
        SELECT tijd, predicted_mw, actual_mw
        FROM predictions
        WHERE actual_mw IS NOT NULL
        ORDER BY tijd DESC
        LIMIT 720
    """
    df = pd.read_sql(query, get_engine())
    print(f"Loaded {len(df)} rows with actuals")
    return df


@task(name="run-evidently")
def run_evidently(df):
    definition = DataDefinition(
        numerical_columns=["predicted_mw", "actual_mw"],
        regression=[Regression(target="actual_mw", prediction="predicted_mw")],
    )

    report = Report(
        [
            RMSE(),
            MAE(),
            MeanError(),
            RegressionPreset(),
        ]
    )

    run = report.run(
        Dataset.from_pandas(df, data_definition=definition),
        None,
    )

    metrics_raw = run.dict()["metrics"]
    metrics = {}
    for m in metrics_raw:
        name = m.get("metric_name", "")
        val = m.get("value")
        if name.startswith("RMSE("):
            metrics["rmse"] = val
        elif name.startswith("MAE("):
            metrics["mae"] = val["mean"] if isinstance(val, dict) else val
        elif name.startswith("MeanError("):
            metrics["me"] = val["mean"] if isinstance(val, dict) else val

    print(
        f"RMSE: {metrics.get('rmse', 0):.2f} MW | MAE: {metrics.get('mae', 0):.2f} MW"
    )
    return metrics


@task(name="save-metrics")
def save_metrics(metrics, row_count):
    ensure_metrics_table()

    with get_engine().connect() as conn:
        conn.execute(
            text("""
            INSERT INTO monitoring_metrics (run_date, rmse, mae, me, row_count)
            VALUES (CURRENT_DATE, :rmse, :mae, :me, :row_count)
        """),
            {
                "rmse": metrics.get("rmse"),
                "mae": metrics.get("mae"),
                "me": metrics.get("me"),
                "row_count": row_count,
            },
        )
        conn.commit()
    print("Saved metrics to monitoring_metrics")


@task(name="check-threshold")
def check_threshold(metrics):
    rmse = metrics.get("rmse")
    if rmse is None:
        print("No RMSE computed, skipping threshold check")
        return

    print(f"RMSE {rmse:.2f} vs threshold {RMSE_THRESHOLD_MW}")
    if rmse > RMSE_THRESHOLD_MW:
        print("RMSE exceeds threshold, triggering retraining")
        try:
            resp = requests.post(
                f"{PREFECT_API_URL}/deployments/filter",
                json={"deployments": {"name": {"any_": ["solar-forecast-training"]}}},
                timeout=10,
            )
            deployments = resp.json()
            if deployments:
                deployment_id = deployments[0]["id"]
                requests.post(
                    f"{PREFECT_API_URL}/deployments/{deployment_id}/create_flow_run",
                    json={},
                    timeout=10,
                )
                print(f"Triggered retraining flow run (deployment {deployment_id})")
            else:
                print("No solar-forecast-training deployment found, skipping trigger")
        except Exception as e:
            print(f"Failed to trigger retraining: {e}")
    else:
        print("RMSE within threshold, no retraining needed")


@flow(name="monitoring-flow")
def monitoring_flow():
    df = load_predictions()
    if df.empty:
        print("No predictions with actuals available, skipping")
        return

    metrics = run_evidently(df)
    save_metrics(metrics, len(df))
    check_threshold(metrics)


if __name__ == "__main__":
    monitoring_flow.serve(
        name="monitoring-flow",
        cron="0 2 * * *",
    )
