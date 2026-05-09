from prefect import flow

from src.hpo import run_optimization
from src.preprocess import (
    add_features,
    load_data,
    load_processed,
    save_processed,
    split,
)
from src.register import run_register
from src.train import run_train

RAW_SUN = "data/raw/sun_combined.csv"
RAW_PROD = "data/raw/productie_comnbined.csv"
PROCESSED = "data/processed/dataset.parquet"


@flow(name="solar-forecast-training")
def training_flow(reprocess=False):
    try:
        if reprocess:
            raise FileNotFoundError
        df = load_processed(PROCESSED)
        print(f"Loaded processed dataset: {len(df)} rows")
    except FileNotFoundError:
        df = load_data(RAW_SUN, RAW_PROD)
        df = add_features(df)
        save_processed(df, PROCESSED)
        print(f"Processed and saved dataset: {len(df)} rows")

    train, val = split(df)
    print(f"Train: {len(train)} rows, Val: {len(val)} rows")

    run_train(train, val)
    run_optimization(train, val)
    run_register(train, val)


if __name__ == "__main__":
    training_flow()
