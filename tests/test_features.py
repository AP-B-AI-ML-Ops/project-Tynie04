import math

import pandas as pd
import pytest


def compute_features(tijd, radiation):
    doy = tijd.timetuple().tm_yday
    return {
        "open_meteo_radiation": radiation,
        "month": tijd.month,
        "sin_day": math.sin(2 * math.pi * doy / 365),
        "cos_day": math.cos(2 * math.pi * doy / 365),
        "sin_hour": math.sin(2 * math.pi * tijd.hour / 24),
        "cos_hour": math.cos(2 * math.pi * tijd.hour / 24),
    }


def test_midnight_sin_hour_is_zero():
    dt = pd.Timestamp("2024-06-01 00:00:00", tz="Europe/Brussels")
    features = compute_features(dt, 0.0)
    assert features["sin_hour"] == pytest.approx(0.0, abs=1e-9)


def test_noon_sin_hour_is_zero():
    dt = pd.Timestamp("2024-06-01 12:00:00", tz="Europe/Brussels")
    features = compute_features(dt, 500.0)
    assert features["sin_hour"] == pytest.approx(0.0, abs=1e-9)


def test_6am_sin_hour_is_one():
    dt = pd.Timestamp("2024-06-01 06:00:00", tz="Europe/Brussels")
    features = compute_features(dt, 200.0)
    assert features["sin_hour"] == pytest.approx(1.0, abs=1e-9)


def test_jan1_cos_day_is_one():
    dt = pd.Timestamp("2024-01-01 12:00:00", tz="Europe/Brussels")
    features = compute_features(dt, 50.0)
    assert features["cos_day"] == pytest.approx(1.0, abs=1e-2)


def test_cyclical_values_in_range():
    dt = pd.Timestamp("2024-06-21 14:00:00", tz="Europe/Brussels")
    features = compute_features(dt, 800.0)
    for key in ["sin_day", "cos_day", "sin_hour", "cos_hour"]:
        assert -1.0 <= features[key] <= 1.0


def test_month_extracted_correctly():
    dt = pd.Timestamp("2024-06-01 10:00:00", tz="Europe/Brussels")
    features = compute_features(dt, 300.0)
    assert features["month"] == 6


def test_radiation_passed_through():
    dt = pd.Timestamp("2024-06-01 10:00:00", tz="Europe/Brussels")
    features = compute_features(dt, 123.45)
    assert features["open_meteo_radiation"] == 123.45
