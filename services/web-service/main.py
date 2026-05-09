import mlflow
import mlflow.pyfunc
import pandas as pd
from flask import Flask, jsonify, request

MLFLOW_TRACKING_URI = "http://experiment-tracking:5000"
MODEL_NAME = "solar-forecast-model"

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

app = Flask("energy-forecast")
model = None


def get_model():
    global model
    if model is None:
        model = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}/latest")
    return model


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()

    features = pd.DataFrame(
        [
            {
                "open_meteo_radiation": data["open_meteo_radiation"],
                "month": data["month"],
                "day_of_year": data["day_of_year"],
            }
        ]
    )

    prediction = float(get_model().predict(features)[0])

    return jsonify({"predicted_zon_kwh": prediction})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
