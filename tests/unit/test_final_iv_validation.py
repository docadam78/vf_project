import datetime as dt
from typing import Dict

import numpy as np
import pytest

from volfitter.config import VolfitterConfig
from volfitter.domain.datamodel import (
    RawIVCurve,
    ok,
    Option,
    Pricing,
    RawIVPoint,
    FinalIVCurve,
    FinalIVPoint,
    Tag,
    fail,
)
from volfitter.domain.final_iv_validation import CrossedPnLFinalIVValidator


@pytest.fixture
def final_iv_validation_config() -> VolfitterConfig.FinalIVValidationConfig:
    return VolfitterConfig.FinalIVValidationConfig.from_environ(
        {
            "FINAL_IV_VALIDATION_CONFIG_CROSSED_PNL_WARN_THRESHOLD": 1,
            "FINAL_IV_VALIDATION_CONFIG_CROSSED_PNL_FAIL_THRESHOLD": 2,
        }
    )


@pytest.fixture
def raw_iv_curve(
    jan_expiry: dt.datetime,
    current_date: dt.date,
    jan_100_call: Option,
    jan_110_call: Option,
) -> RawIVCurve:
    return RawIVCurve(
        jan_expiry,
        ok(),
        {
            jan_100_call: RawIVPoint(jan_100_call, current_date, 9, 10),
            jan_110_call: RawIVPoint(jan_110_call, current_date, np.nan, 11),
        },
    )


@pytest.fixture
def pricing(jan_100_call: Option, jan_110_call: Option) -> Dict[Option, Pricing]:
    return {
        jan_100_call: pricing_with_vega(jan_100_call, 1.1),
        jan_110_call: pricing_with_vega(jan_110_call, 2.2),
    }


def pricing_with_vega(option: Option, vega: float) -> Pricing:
    return Pricing(option, 0, 0, 0, vega, 0, 0)


def test_crossed_pnl_validator_sets_status_to_fail_when_fail_threshold_breached(
    jan_expiry: dt.datetime,
    final_iv_validation_config: VolfitterConfig.FinalIVValidationConfig,
    raw_iv_curve: RawIVCurve,
    pricing: Dict[Option, Pricing],
):
    final_iv_curve = FinalIVCurve(
        jan_expiry,
        ok(),
        {
            100: FinalIVPoint(jan_expiry, 100, 11),
            110: FinalIVPoint(jan_expiry, 110, 12),
        },
    )

    victim = CrossedPnLFinalIVValidator(final_iv_validation_config)

    validated_curve = victim._validate_expiry(final_iv_curve, raw_iv_curve, pricing)

    assert validated_curve.status.tag == Tag.FAIL
    assert "Crossed PnL" in validated_curve.status.message
    assert validated_curve.points == final_iv_curve.points


def test_crossed_pnl_validator_sets_status_to_warn_when_warn_threshold_breached(
    jan_expiry: dt.datetime,
    final_iv_validation_config: VolfitterConfig.FinalIVValidationConfig,
    raw_iv_curve: RawIVCurve,
    pricing: Dict[Option, Pricing],
):
    final_iv_curve = FinalIVCurve(
        jan_expiry,
        ok(),
        {
            100: FinalIVPoint(jan_expiry, 100, 11),
            110: FinalIVPoint(jan_expiry, 110, 8),
        },
    )

    victim = CrossedPnLFinalIVValidator(final_iv_validation_config)

    validated_curve = victim._validate_expiry(final_iv_curve, raw_iv_curve, pricing)

    assert validated_curve.status.tag == Tag.WARN
    assert "Crossed PnL" in validated_curve.status.message
    assert validated_curve.points == final_iv_curve.points


def test_crossed_pnl_validator_leaves_curve_unchanged_if_it_does_not_breach_threshold(
    jan_expiry: dt.datetime,
    final_iv_validation_config: VolfitterConfig.FinalIVValidationConfig,
    raw_iv_curve: RawIVCurve,
    pricing: Dict[Option, Pricing],
):
    final_iv_curve = FinalIVCurve(
        jan_expiry,
        ok(),
        {
            100: FinalIVPoint(jan_expiry, 100, 10.5),
            110: FinalIVPoint(jan_expiry, 110, 8),
        },
    )

    victim = CrossedPnLFinalIVValidator(final_iv_validation_config)

    validated_curve = victim._validate_expiry(final_iv_curve, raw_iv_curve, pricing)

    assert validated_curve == final_iv_curve


def test_crossed_pnl_validator_propagates_preexisting_failure(
    jan_expiry: dt.datetime,
    final_iv_validation_config: VolfitterConfig.FinalIVValidationConfig,
    raw_iv_curve: RawIVCurve,
    pricing: Dict[Option, Pricing],
):
    final_iv_curve = FinalIVCurve(
        jan_expiry,
        fail("a message"),
        {
            100: FinalIVPoint(jan_expiry, 100, 11),
            110: FinalIVPoint(jan_expiry, 110, 12),
        },
    )

    victim = CrossedPnLFinalIVValidator(final_iv_validation_config)

    validated_curve = victim._validate_expiry(final_iv_curve, raw_iv_curve, pricing)

    assert validated_curve == final_iv_curve
