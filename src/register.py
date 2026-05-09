import mlflow
import mlflow.sklearn
from mlflow.entities import ViewType
from mlflow.tracking import MlflowClient
from prefect import task
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import root_mean_squared_error

from src.preprocess import FEATURES_DAILY, FEATURES_HOURLY, TARGET


@task
def run_register(train, val, granularity="daily", top_n=3):
    features = FEATURES_DAILY if granularity == "daily" else FEATURES_HOURLY
    model_name = f"solar-forecast-model-{granularity}"

    mlflow.set_tracking_uri("http://experiment-tracking:5000")
    client = MlflowClient()

    X_train = train[features]
    y_train = train[TARGET]
    X_val = val[features]
    y_val = val[TARGET]

    experiment = client.get_experiment_by_name(f"solar-forecast-hpo-{granularity}")
    top_runs = client.search_runs(
        experiment_ids=experiment.experiment_id,
        run_view_type=ViewType.ACTIVE_ONLY,
        max_results=top_n,
        order_by=["metrics.rmse ASC"],
    )

    mlflow.set_experiment(f"solar-forecast-best-models-{granularity}")
    mlflow.sklearn.autolog(disable=True)

    best_rmse = float("inf")
    best_model = None
    best_params = None

    for run in top_runs:
        params = {
            k: int(v)
            for k, v in run.data.params.items()
            if k
            in [
                "n_estimators",
                "max_depth",
                "min_samples_split",
                "min_samples_leaf",
                "random_state",
            ]
        }
        params["n_jobs"] = -1

        model = RandomForestRegressor(**params)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_val)
        rmse = root_mean_squared_error(y_val, y_pred)

        if rmse < best_rmse:
            best_rmse = rmse
            best_model = model
            best_params = params

    with mlflow.start_run():
        mlflow.set_tag("granularity", granularity)
        mlflow.log_params(best_params)
        mlflow.log_metric("rmse", best_rmse)
        mlflow.sklearn.log_model(
            best_model, artifact_path="model", registered_model_name=model_name
        )

    print(f"Registered '{model_name}' (RMSE: {best_rmse:.2f})")
