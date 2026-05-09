from prefect import flow


@flow
def monitor():
    # TODO: compare predictions against Elia actuals, report to Evidently + Grafana
    print("monitor flow started — not yet implemented")


if __name__ == "__main__":
    monitor.serve(name="monitoring")
