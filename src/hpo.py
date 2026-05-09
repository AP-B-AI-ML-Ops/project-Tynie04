import mlflow
import mlflow.sklearn
import optuna
from prefect import task
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import root_mean_squared_error

from src.preprocess import FEATURES, TARGET


@task
def run_optimization(train, val, num_trials=20):
    mlflow.set_tracking_uri("http://experiment-tracking:5000")
    mlflow.set_experiment("solar-forecast-hpo")
    mlflow.sklearn.autolog(disable=True)

    X_train = train[FEATURES]
    y_train = train[TARGET]
    X_val = val[FEATURES]
    y_val = val[TARGET]

    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 10, 200),
            "max_depth": trial.suggest_int("max_depth", 2, 20),
            "min_samples_split": trial.suggest_int("min_samples_split", 2, 10),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 4),
            "random_state": 42,
            "n_jobs": -1,
        }

        with mlflow.start_run():
            mlflow.log_params(params)
            model = RandomForestRegressor(**params)
            model.fit(X_train, y_train)
            y_pred = model.predict(X_val)
            rmse = root_mean_squared_error(y_val, y_pred)
            mlflow.log_metric("rmse", rmse)

        return rmse

    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=num_trials)

    print(f"Best RMSE: {study.best_value:.2f}")
    print(f"Best params: {study.best_params}")
