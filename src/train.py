import mlflow
import mlflow.sklearn
from prefect import task
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import root_mean_squared_error

from src.preprocess import FEATURES, TARGET


@task
def run_train(train, val):
    mlflow.set_tracking_uri("http://experiment-tracking:5000")
    mlflow.set_experiment("solar-forecast-train")
    mlflow.sklearn.autolog()

    X_train = train[FEATURES]
    y_train = train[TARGET]
    X_val = val[FEATURES]
    y_val = val[TARGET]

    with mlflow.start_run():
        model = RandomForestRegressor(max_depth=10, random_state=42, n_jobs=-1)
        model.fit(X_train, y_train)

        y_pred = model.predict(X_val)
        rmse = root_mean_squared_error(y_val, y_pred)
        mlflow.log_metric("rmse", rmse)

        print(f"RMSE: {rmse:.2f}")
