from prefect import flow


@flow
def batch_forecast():
    # TODO: fetch ECMWF forecast, run inference, store predictions
    print("batch_forecast flow started — not yet implemented")


if __name__ == "__main__":
    batch_forecast.serve(name="batch-forecast")
