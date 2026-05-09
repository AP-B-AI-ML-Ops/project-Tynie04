from flask import Flask, jsonify

app = Flask("energy-forecast")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/predict", methods=["POST"])
def predict():
    # TODO: load model from MLflow and return forecast
    return jsonify({"error": "not implemented"}), 501


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
