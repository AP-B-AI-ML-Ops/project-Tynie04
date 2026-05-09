import mlflow
import mlflow.sklearn
from mlflow.entities import ViewType
from mlflow.tracking import MlflowClient
from prefect import task
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import root_mean_squared_error

from src.preprocess import FEATURES, TARGET

MODEL_NAME = "solar-forecast-model"


@task
def run_register(train, val, top_n=3):
    mlflow.set_tracking_uri("http://experiment-tracking:5000")
    client = MlflowClient()

    X_train = train[FEATURES]
    y_train = train[TARGET]
    X_val = val[FEATURES]
    y_val = val[TARGET]

    experiment = client.get_experiment_by_name("solar-forecast-hpo")
    top_runs = client.search_runs(
        experiment_ids=experiment.experiment_id,
        run_view_type=ViewType.ACTIVE_ONLY,
        max_results=top_n,
        order_by=["metrics.rmse ASC"],
    )

    mlflow.set_experiment("solar-forecast-best-models")
    mlflow.sklearn.autolog(disable=True)

    for run in top_runs:
        params = {
            k: int(v) if k != "random_state" and k != "n_jobs" else int(v)
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

        with mlflow.start_run():
            model = RandomForestRegressor(**params)
            model.fit(X_train, y_train)
            y_pred = model.predict(X_val)
            rmse = root_mean_squared_error(y_val, y_pred)
            mlflow.log_params(params)
            mlflow.log_metric("rmse", rmse)
            mlflow.sklearn.log_model(model, artifact_path="model")

    best_run = client.search_runs(
        experiment_ids=client.get_experiment_by_name(
            "solar-forecast-best-models"
        ).experiment_id,
        run_view_type=ViewType.ACTIVE_ONLY,
        max_results=1,
        order_by=["metrics.rmse ASC"],
    )[0]

    model_uri = f"runs:/{best_run.info.run_id}/model"
    mlflow.register_model(model_uri, name=MODEL_NAME)

    print(
        f"Registered model '{MODEL_NAME}' from run {best_run.info.run_id} (RMSE: {best_run.data.metrics['rmse']:.2f})"
    )
