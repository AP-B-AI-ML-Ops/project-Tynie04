import mlflow
import mlflow.sklearn
from prefect import task
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import root_mean_squared_error

from src.preprocess import FEATURES_DAILY, FEATURES_HOURLY, TARGET


@task
def run_train(train, val, granularity="daily"):
    features = FEATURES_DAILY if granularity == "daily" else FEATURES_HOURLY

    mlflow.set_tracking_uri("http://experiment-tracking:5000")
    mlflow.set_experiment(f"solar-forecast-train-{granularity}")
    mlflow.sklearn.autolog()

    X_train = train[features]
    y_train = train[TARGET]
    X_val = val[features]
    y_val = val[TARGET]

    with mlflow.start_run():
        mlflow.set_tag("granularity", granularity)
        model = RandomForestRegressor(max_depth=10, random_state=42, n_jobs=-1)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_val)
        rmse = root_mean_squared_error(y_val, y_pred)
        mlflow.log_metric("rmse", rmse)
        print(f"[{granularity}] RMSE: {rmse:.2f}")
