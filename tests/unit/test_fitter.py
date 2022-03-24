import datetime as dt
from typing import Dict
from unittest.mock import Mock

import numpy as np
import pytest

from tests.assertions import assert_curve_approx_equal
from volfitter.domain.datamodel import (
    Option,
    RawIVCurve,
    RawIVPoint,
    ok,
    fail,
    Tag,
    SVIParameters,
    Pricing,
    Status,
    FinalIVCurve,
    FinalIVPoint,
)
from volfitter.domain.fitter import (
    MidMarketSurfaceFitter,
    UnconstrainedQuasiExplicitSVICalibrator,
    _svi_implied_variance,
    AbstractSVICalibrator,
    SVISurfaceFitter,
)


@pytest.fixture
def raw_iv_curve(
    current_date: dt.date,
    jan_expiry: dt.datetime,
    jan_100_call: Option,
    jan_100_put: Option,
    jan_110_call: Option,
    jan_110_put: Option,
) -> RawIVCurve:
    return RawIVCurve(
        jan_expiry,
        ok(),
        {
            jan_100_call: RawIVPoint(jan_100_call, current_date, 1.1, 1.9),
            jan_100_put: RawIVPoint(jan_100_put, current_date, 1.0, 2.0),
            jan_110_call: RawIVPoint(jan_110_call, current_date, 1.1, 1.9),
            jan_110_put: RawIVPoint(jan_110_put, current_date, 1.2, 2.2),
        },
    )


@pytest.fixture
def pricing(
    jan_100_call: Option,
    jan_100_put: Option,
    jan_110_call: Option,
    jan_110_put: Option,
):
    return {
        jan_100_call: pricing_with_moneyness_and_time_to_expiry(jan_100_call, 1, 2),
        jan_100_put: pricing_with_moneyness_and_time_to_expiry(jan_100_put, 1, 2),
        jan_110_call: pricing_with_moneyness_and_time_to_expiry(jan_110_call, 3, 2),
        jan_110_put: pricing_with_moneyness_and_time_to_expiry(jan_110_put, 3, 2),
    }


def pricing_with_moneyness_and_time_to_expiry(
    option: Option, moneyness: float, time_to_expiry: float
) -> Pricing:
    return Pricing(option, moneyness, 0, 0, 0, 0, time_to_expiry)


def test_when_fitted_to_an_svi_curve_calibrator_recovers_input_curve_parameters(
    jan_expiry: dt.datetime,
):
    # These parameters reproduce the experiment in Section 4 of Zeliade 2012
    expected_level = 0.04
    expected_angle = 0.1
    expected_smoothness = 0.1
    expected_tilt = -0.5
    expected_center = 0.0

    moneyness = np.array([-0.5, -0.4, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5])
    variance = _svi_implied_variance(
        moneyness,
        expected_level,
        expected_angle,
        expected_smoothness,
        expected_tilt,
        expected_center,
    )
    time_to_expiry = 1.0

    victim = UnconstrainedQuasiExplicitSVICalibrator()

    svi_parameters, status = victim.calibrate(
        jan_expiry, moneyness, variance, time_to_expiry
    )

    assert status.tag == Tag.OK
    assert pytest.approx(svi_parameters.level, abs=1e-5) == expected_level
    assert pytest.approx(svi_parameters.angle, abs=1e-5) == expected_angle
    assert pytest.approx(svi_parameters.smoothness, abs=1e-4) == expected_smoothness
    assert pytest.approx(svi_parameters.tilt, abs=1e-4) == expected_tilt
    assert pytest.approx(svi_parameters.center, abs=1e-5) == expected_center


def test_svi_fitter_produces_final_curve_from_calibrated_svi_parameters(
    raw_iv_curve: RawIVCurve, pricing: Dict[Option, Pricing]
):
    svi_parameters = SVIParameters(0.04, 0.1, 0.1, -0.5, 0.0)
    status = Status(Tag.OK, "a message")

    calibrator = Mock(spec_set=AbstractSVICalibrator)
    calibrator.calibrate.return_value = svi_parameters, status

    expected_final_iv_curve = FinalIVCurve(
        raw_iv_curve.expiry,
        status,
        {
            100: FinalIVPoint(raw_iv_curve.expiry, 100, 0.301),
            110: FinalIVPoint(raw_iv_curve.expiry, 110, 0.436),
        },
    )

    victim = SVISurfaceFitter(calibrator)

    final_iv_curve = victim._fit_curve_model(raw_iv_curve, pricing)

    assert_curve_approx_equal(final_iv_curve, expected_final_iv_curve, abs=1e-3)


def test_svi_fitter_propagates_input_curve_failure(
    current_date: dt.date, jan_expiry: dt.datetime, jan_100_call: Option
):
    message = "'Failure is a part of the process.' -- Michelle Obama"
    raw_iv_curve = RawIVCurve(
        jan_expiry,
        fail(message),
        {
            jan_100_call: RawIVPoint(jan_100_call, current_date, 1, 2),
        },
    )
    victim = SVISurfaceFitter(Mock(spec_set=AbstractSVICalibrator))

    final_iv_curve = victim._fit_curve_model(raw_iv_curve, {})

    assert final_iv_curve.status.tag == Tag.FAIL
    assert final_iv_curve.status.message == message
    assert len(final_iv_curve.points) == 0


def test_mid_market_fitter_returns_midpoint_vol_per_strike(raw_iv_curve: RawIVCurve):
    victim = MidMarketSurfaceFitter()

    final_iv_curve = victim._fit_curve_model(raw_iv_curve, {})

    assert pytest.approx(final_iv_curve.points[100].vol) == (1.1 + 1.9) / 2
    assert pytest.approx(final_iv_curve.points[110].vol) == (1.2 + 1.9) / 2


def test_mid_market_fitter_propagates_input_curve_failure(
    current_date: dt.date, jan_expiry: dt.datetime, jan_100_call: Option
):
    message = "'Failure is a part of the process.' -- Michelle Obama"
    raw_iv_curve = RawIVCurve(
        jan_expiry,
        fail(message),
        {
            jan_100_call: RawIVPoint(jan_100_call, current_date, 1, 2),
        },
    )
    victim = MidMarketSurfaceFitter()

    final_iv_curve = victim._fit_curve_model(raw_iv_curve, {})

    assert final_iv_curve.status.tag == Tag.FAIL
    assert final_iv_curve.status.message == message
    assert len(final_iv_curve.points) == 0
