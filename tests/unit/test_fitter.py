import datetime as dt
import pytest

from volfitter.domain.datamodel import (
    Option,
    OptionKind,
    ExerciseStyle,
    RawIVCurve,
    RawIVPoint,
)
from volfitter.domain.fitter import PassThroughSurfaceFitter

_EXPIRY = dt.datetime(2020, 2, 3, 15, 0)


def test_pass_through_fitter_returns_midpoint_vol_per_strike():
    option_1 = _create_option(100, OptionKind.CALL)
    option_2 = _create_option(100, OptionKind.PUT)
    option_3 = _create_option(200, OptionKind.CALL)
    option_4 = _create_option(200, OptionKind.PUT)

    raw_iv_curve = RawIVCurve(
        _EXPIRY,
        {
            option_1: RawIVPoint(option_1, 1.1, 1.9),
            option_2: RawIVPoint(option_2, 1.0, 2.0),
            option_3: RawIVPoint(option_3, 1.1, 1.9),
            option_4: RawIVPoint(option_4, 1.2, 2.2),
        },
    )
    victim = PassThroughSurfaceFitter()

    final_iv_curve = victim._fit_curve_model(raw_iv_curve)

    assert pytest.approx(final_iv_curve.points[100].vol) == (1.1 + 1.9) / 2
    assert pytest.approx(final_iv_curve.points[200].vol) == (1.2 + 1.9) / 2


def _create_option(strike: float, option_kind: OptionKind) -> Option:
    return Option("AMZN", _EXPIRY, strike, option_kind, ExerciseStyle.AMERICAN, 100)
