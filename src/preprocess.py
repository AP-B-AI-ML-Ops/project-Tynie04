import pandas as pd


def load_data(sun_path, production_path):
    sun = pd.read_csv(sun_path)
    prod = pd.read_csv(production_path)

    sun["datum"] = pd.to_datetime(sun["datum"]).dt.tz_localize(None).dt.normalize()
    prod["tijd"] = pd.to_datetime(prod["tijd"], utc=True).dt.tz_localize(None)

    prod_daily = (
        prod.groupby(prod["tijd"].dt.normalize())
        .agg(zon_kwh=("elia zon kwh", "sum"), wind_kwh=("elia wind kwh", "sum"))
        .reset_index()
        .rename(columns={"tijd": "datum"})
    )

    merged = pd.merge(
        prod_daily,
        sun[["datum", "open_meteo_radiation"]],
        on="datum",
        how="inner",
    )

    merged = merged.dropna(subset=["zon_kwh", "open_meteo_radiation"])
    merged = merged.sort_values("datum").reset_index(drop=True)

    return merged


def add_features(df):
    df = df.copy()
    df["month"] = df["datum"].dt.month
    df["day_of_year"] = df["datum"].dt.dayofyear
    return df


def split(df, val_fraction=0.2):
    split_idx = int(len(df) * (1 - val_fraction))
    train = df.iloc[:split_idx].reset_index(drop=True)
    val = df.iloc[split_idx:].reset_index(drop=True)
    return train, val


def save_processed(df, output_path):
    df.to_parquet(output_path, index=False)


def load_processed(input_path):
    return pd.read_parquet(input_path)


FEATURES = ["open_meteo_radiation", "month", "day_of_year"]
TARGET = "zon_kwh"
