import numpy as np
import pandas as pd

from src.preprocess import add_features, split


def make_daily_df(n=10):
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {
            "datum": dates,
            "open_meteo_radiation": np.linspace(100, 500, n),
            "zon_kwh": np.linspace(10, 50, n),
        }
    )


def make_hourly_df(n=24):
    times = pd.date_range("2024-06-01", periods=n, freq="h")
    return pd.DataFrame(
        {
            "tijd": times,
            "datum": times.normalize(),
            "open_meteo_radiation": np.linspace(0, 800, n),
            "zon_kwh": np.linspace(0, 40, n),
        }
    )


def test_add_features_daily_adds_cyclical_columns():
    df = make_daily_df()
    result = add_features(df, granularity="daily")
    assert "month" in result.columns
    assert "sin_day" in result.columns
    assert "cos_day" in result.columns


def test_add_features_daily_no_hour_columns():
    df = make_daily_df()
    result = add_features(df, granularity="daily")
    assert "sin_hour" not in result.columns
    assert "cos_hour" not in result.columns


def test_add_features_hourly_adds_hour_columns():
    df = make_hourly_df()
    result = add_features(df, granularity="hourly")
    assert "sin_hour" in result.columns
    assert "cos_hour" in result.columns


def test_add_features_cyclical_values_in_range():
    df = make_daily_df()
    result = add_features(df, granularity="daily")
    assert result["sin_day"].between(-1, 1).all()
    assert result["cos_day"].between(-1, 1).all()


def test_split_correct_sizes():
    df = make_daily_df(10)
    train, val = split(df, val_fraction=0.2)
    assert len(train) == 8
    assert len(val) == 2


def test_split_preserves_order():
    df = make_daily_df(10)
    train, val = split(df, val_fraction=0.2)
    assert train["datum"].iloc[-1] < val["datum"].iloc[0]
