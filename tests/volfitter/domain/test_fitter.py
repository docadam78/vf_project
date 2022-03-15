import datetime as dt
import pytest

from src.volfitter.domain.datamodel import (
    Option,
    OptionKind,
    ExerciseStyle,
    RawIVCurve,
    RawIVPoint,
)
from src.volfitter.domain.fitter import PassThroughSurfaceFitter

_EXPIRY = dt.datetime(2020, 2, 3, 15, 0)


def test_pass_through_fitter_returns_midpoint_vol_per_strike():
    raw_iv_curve = RawIVCurve(
        _EXPIRY,
        {
            _create_raw_iv_point(100, OptionKind.CALL, 1.1, 1.9),
            _create_raw_iv_point(100, OptionKind.PUT, 1.0, 2.0),
            _create_raw_iv_point(200, OptionKind.CALL, 1.1, 1.9),
            _create_raw_iv_point(200, OptionKind.PUT, 1.2, 2.2),
        },
    )
    victim = PassThroughSurfaceFitter()

    final_iv_curve = victim._fit_curve_model(raw_iv_curve)

    assert pytest.approx(final_iv_curve.points[100].vol) == (1.1 + 1.9) / 2
    assert pytest.approx(final_iv_curve.points[200].vol) == (1.2 + 1.9) / 2


def _create_raw_iv_point(
    strike: float, option_kind: OptionKind, bid_vol: float, ask_vol: float
) -> RawIVPoint:
    option = Option("AMZN", _EXPIRY, strike, option_kind, ExerciseStyle.AMERICAN, 100)
    return RawIVPoint(option, bid_vol, ask_vol)
