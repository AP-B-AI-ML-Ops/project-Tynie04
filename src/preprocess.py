import numpy as np
import pandas as pd

FEATURES_DAILY = ["open_meteo_radiation", "month", "sin_day", "cos_day"]
FEATURES_HOURLY = [
    "open_meteo_radiation",
    "month",
    "sin_day",
    "cos_day",
    "sin_hour",
    "cos_hour",
]
TARGET = "zon_kwh"


def load_data(sun_path, production_path, granularity="daily"):
    sun = pd.read_csv(sun_path)
    prod = pd.read_csv(production_path)

    sun["datum"] = pd.to_datetime(sun["datum"]).dt.tz_localize(None).dt.normalize()
    prod["tijd"] = pd.to_datetime(prod["tijd"], utc=True).dt.tz_localize(None)
    prod["datum"] = prod["tijd"].dt.normalize()

    if granularity == "daily":
        prod_agg = (
            prod.groupby("datum").agg(zon_kwh=("elia zon kwh", "sum")).reset_index()
        )
        merged = pd.merge(
            prod_agg, sun[["datum", "open_meteo_radiation"]], on="datum", how="inner"
        )
        merged = merged.dropna(subset=["zon_kwh", "open_meteo_radiation"])
        merged = merged.sort_values("datum").reset_index(drop=True)
    else:
        merged = pd.merge(
            prod, sun[["datum", "open_meteo_radiation"]], on="datum", how="inner"
        )
        merged = merged.rename(columns={"elia zon kwh": "zon_kwh"})
        merged = merged.dropna(subset=["zon_kwh", "open_meteo_radiation"])
        merged = merged.sort_values("tijd").reset_index(drop=True)

    return merged


def add_features(df, granularity="daily"):
    df = df.copy()
    df["month"] = df["datum"].dt.month
    df["day_of_year"] = df["datum"].dt.dayofyear
    df["sin_day"] = np.sin(2 * np.pi * df["day_of_year"] / 365)
    df["cos_day"] = np.cos(2 * np.pi * df["day_of_year"] / 365)

    if granularity == "hourly":
        df["hour"] = df["tijd"].dt.hour
        df["sin_hour"] = np.sin(2 * np.pi * df["hour"] / 24)
        df["cos_hour"] = np.cos(2 * np.pi * df["hour"] / 24)

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
