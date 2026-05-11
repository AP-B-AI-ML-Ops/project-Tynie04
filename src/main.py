import shutil

from prefect import flow

from src.hpo import run_optimization
from src.preprocess import add_features, load_data, save_processed, split
from src.register import run_register
from src.train import run_train

RAW_SUN = "data/raw/sun_combined.csv"
RAW_PROD = "data/raw/productie_comnbined.csv"
BATCH_DATA_PATH = "/batch-data/dataset_hourly.parquet"


@flow(name="solar-forecast-training")
def training_flow():
    for granularity in ["daily", "hourly"]:
        processed_path = f"data/processed/dataset_{granularity}.parquet"

        df = load_data(RAW_SUN, RAW_PROD, granularity=granularity)
        df = add_features(df, granularity=granularity)
        save_processed(df, processed_path)
        print(f"[{granularity}] Dataset: {len(df)} rows")

        if granularity == "hourly":
            shutil.copy(processed_path, BATCH_DATA_PATH)
            print(f"Copied hourly dataset to {BATCH_DATA_PATH}")

        train, val = split(df)
        print(f"[{granularity}] Train: {len(train)}, Val: {len(val)}")

        run_train(train, val, granularity=granularity)
        run_optimization(train, val, granularity=granularity)
        run_register(train, val, granularity=granularity)


if __name__ == "__main__":
    training_flow.serve(name="solar-forecast-training")
