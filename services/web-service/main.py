import math
from datetime import datetime

import mlflow
import mlflow.pyfunc
import pandas as pd
from flask import Flask, jsonify, request

MLFLOW_TRACKING_URI = "http://experiment-tracking:5000"

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

app = Flask("energy-forecast")
models = {}


def get_model(granularity):
    if granularity not in models:
        models[granularity] = mlflow.pyfunc.load_model(
            f"models:/solar-forecast-model-{granularity}/latest"
        )
    return models[granularity]


def compute_features(dt, open_meteo_radiation, granularity):
    day_of_year = dt.timetuple().tm_yday
    features = {
        "open_meteo_radiation": open_meteo_radiation,
        "month": dt.month,
        "sin_day": math.sin(2 * math.pi * day_of_year / 365),
        "cos_day": math.cos(2 * math.pi * day_of_year / 365),
    }
    if granularity == "hourly":
        features["sin_hour"] = math.sin(2 * math.pi * dt.hour / 24)
        features["cos_hour"] = math.cos(2 * math.pi * dt.hour / 24)
    return features


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    granularity = data.get("granularity", "daily")

    if granularity not in ("daily", "hourly"):
        return jsonify({"error": "granularity must be 'daily' or 'hourly'"}), 400

    try:
        dt = datetime.fromisoformat(data["datetime"])
    except (KeyError, ValueError):
        return jsonify(
            {
                "error": "datetime must be a valid ISO 8601 string, e.g. '2024-06-21' or '2024-06-21T14:00:00'"
            }
        ), 400

    try:
        open_meteo_radiation = float(data["open_meteo_radiation"])
    except (KeyError, ValueError):
        return jsonify({"error": "open_meteo_radiation must be a number"}), 400

    features = compute_features(dt, open_meteo_radiation, granularity)
    df = pd.DataFrame([features])
    prediction = float(get_model(granularity).predict(df)[0])

    return jsonify(
        {
            "predicted_zon_kwh": prediction,
            "granularity": granularity,
            "datetime": dt.isoformat(),
        }
    )


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8000)
