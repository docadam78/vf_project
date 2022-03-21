import datetime as dt
import pytest

from volfitter.domain.datamodel import (
    Option,
    RawIVCurve,
    RawIVPoint,
)
from volfitter.domain.fitter import PassThroughSurfaceFitter


def test_pass_through_fitter_returns_midpoint_vol_per_strike(
    jan_expiry: dt.datetime,
    jan_100_call: Option,
    jan_100_put: Option,
    jan_110_call: Option,
    jan_110_put: Option,
):
    raw_iv_curve = RawIVCurve(
        jan_expiry,
        {
            jan_100_call: RawIVPoint(jan_100_call, 1.1, 1.9),
            jan_100_put: RawIVPoint(jan_100_put, 1.0, 2.0),
            jan_110_call: RawIVPoint(jan_110_call, 1.1, 1.9),
            jan_110_put: RawIVPoint(jan_110_put, 1.2, 2.2),
        },
    )
    victim = PassThroughSurfaceFitter()

    final_iv_curve = victim._fit_curve_model(raw_iv_curve)

    assert pytest.approx(final_iv_curve.points[100].vol) == (1.1 + 1.9) / 2
    assert pytest.approx(final_iv_curve.points[110].vol) == (1.2 + 1.9) / 2
