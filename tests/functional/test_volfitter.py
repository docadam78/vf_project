import datetime as dt
from typing import Dict

import pytest

from unittest.mock import Mock

from tests.assertions import assert_surface_approx_equal
from volfitter.adapters.current_time_supplier import AbstractCurrentTimeSupplier
from volfitter.adapters.final_iv_consumer import AbstractFinalIVConsumer
from volfitter.adapters.forward_curve_supplier import AbstractForwardCurveSupplier
from volfitter.adapters.pricing_supplier import AbstractPricingSupplier
from volfitter.adapters.raw_iv_supplier import AbstractRawIVSupplier
from volfitter.composition_root import create_volfitter_service_from_adaptors
from volfitter.config import VolfitterConfig
from volfitter.domain.datamodel import (
    RawIVSurface,
    Option,
    RawIVCurve,
    RawIVPoint,
    FinalIVCurve,
    FinalIVPoint,
    FinalIVSurface,
    ForwardCurve,
    Pricing,
    ok,
)
from volfitter.service_layer.service import VolfitterService


@pytest.fixture
def volfitter_config() -> VolfitterConfig:
    # If from_environ is passed a dict, it will read its parameters from that
    # "environment" rather than from the process's env vars. Passing an empty dict
    # ensures the default parameters are used, regardless of what env vars may be set.
    return VolfitterConfig.from_environ({})


@pytest.fixture
def forward_curve(
    current_time: dt.datetime, jan_expiry: dt.datetime, feb_expiry: dt.datetime
) -> ForwardCurve:
    return ForwardCurve(current_time, {jan_expiry: 100, feb_expiry: 101})


@pytest.fixture
def pricing(
    jan_90_call: Option,
    jan_90_put: Option,
    jan_100_call: Option,
    jan_100_put: Option,
    jan_110_call: Option,
    jan_110_put: Option,
    feb_90_call: Option,
    feb_90_put: Option,
    feb_100_call: Option,
    feb_100_put: Option,
    feb_110_call: Option,
    feb_110_put: Option,
) -> Dict[Option, Pricing]:
    return {
        jan_90_call: Pricing(jan_90_call, -0.105, 123, 123, 150, 123, 0.08),
        jan_90_put: Pricing(jan_90_put, -0.105, 123, 123, 150, 123, 0.08),
        jan_100_call: Pricing(jan_100_call, 0, 123, 123, 200, 123, 0.08),
        jan_100_put: Pricing(jan_100_put, 0, 123, 123, 200, 123, 0.08),
        jan_110_call: Pricing(jan_110_call, 0.95, 123, 123, 160, 123, 0.08),
        jan_110_put: Pricing(jan_110_put, 0.95, 123, 123, 160, 123, 0.08),
        feb_90_call: Pricing(feb_90_call, -0.115, 123, 123, 160, 123, 0.16),
        feb_90_put: Pricing(feb_90_put, -0.115, 123, 123, 160, 123, 0.16),
        feb_100_call: Pricing(feb_100_call, -0.001, 123, 123, 210, 123, 0.16),
        feb_100_put: Pricing(feb_100_put, -0.001, 123, 123, 210, 123, 0.16),
        feb_110_call: Pricing(feb_110_call, 0.085, 123, 123, 170, 123, 0.16),
        feb_110_put: Pricing(feb_110_put, 0.085, 123, 123, 170, 123, 0.16),
    }


@pytest.fixture
def jan_raw_iv_curve(
    current_date: dt.date,
    jan_expiry: dt.datetime,
    jan_90_call: Option,
    jan_90_put: Option,
    jan_100_call: Option,
    jan_100_put: Option,
    jan_110_call: Option,
    jan_110_put: Option,
) -> RawIVCurve:
    return RawIVCurve(
        jan_expiry,
        ok(),
        {
            jan_90_call: RawIVPoint(jan_90_call, current_date, 0.14, 0.16),
            jan_90_put: RawIVPoint(jan_90_put, current_date, 0.145, 0.155),
            jan_100_call: RawIVPoint(jan_100_call, current_date, 0.129, 0.131),
            jan_100_put: RawIVPoint(jan_100_put, current_date, 0.129, 0.131),
            jan_110_call: RawIVPoint(jan_110_call, current_date, 0.13, 0.14),
            jan_110_put: RawIVPoint(jan_110_put, current_date, 0.125, 0.145),
        },
    )


@pytest.fixture()
def expected_jan_final_iv_curve(jan_expiry: dt.datetime) -> FinalIVCurve:
    return FinalIVCurve(
        jan_expiry,
        ok(),
        {
            90: FinalIVPoint(jan_expiry, 90, 0.15),
            100: FinalIVPoint(jan_expiry, 100, 0.13),
            110: FinalIVPoint(jan_expiry, 110, 0.135),
        },
    )


@pytest.fixture
def feb_raw_iv_curve(
    current_date: dt.date,
    feb_expiry: dt.datetime,
    feb_90_call: Option,
    feb_90_put: Option,
    feb_100_call: Option,
    feb_100_put: Option,
    feb_110_call: Option,
    feb_110_put: Option,
) -> RawIVCurve:
    return RawIVCurve(
        feb_expiry,
        ok(),
        {
            feb_90_call: RawIVPoint(feb_90_call, current_date, 0.23, 0.25),
            feb_90_put: RawIVPoint(feb_90_put, current_date, 0.235, 0.245),
            feb_100_call: RawIVPoint(feb_100_call, current_date, 0.229, 0.231),
            feb_100_put: RawIVPoint(feb_100_put, current_date, 0.229, 0.231),
            feb_110_call: RawIVPoint(feb_110_call, current_date, 0.22, 0.23),
            feb_110_put: RawIVPoint(feb_110_put, current_date, 0.215, 0.235),
        },
    )


@pytest.fixture()
def expected_feb_final_iv_curve(feb_expiry: dt.datetime) -> FinalIVCurve:
    return FinalIVCurve(
        feb_expiry,
        ok(),
        {
            90: FinalIVPoint(feb_expiry, 90, 0.24),
            100: FinalIVPoint(feb_expiry, 100, 0.23),
            110: FinalIVPoint(feb_expiry, 110, 0.225),
        },
    )


@pytest.fixture
def raw_iv_surface(
    current_time: dt.datetime,
    jan_raw_iv_curve: RawIVCurve,
    feb_raw_iv_curve: RawIVCurve,
) -> RawIVSurface:
    return RawIVSurface(
        current_time,
        {
            jan_raw_iv_curve.expiry: jan_raw_iv_curve,
            feb_raw_iv_curve.expiry: feb_raw_iv_curve,
        },
    )


@pytest.fixture
def expected_final_iv_surface(
    current_time: dt.datetime,
    expected_jan_final_iv_curve: FinalIVCurve,
    expected_feb_final_iv_curve: FinalIVCurve,
) -> FinalIVSurface:
    return FinalIVSurface(
        current_time,
        {
            expected_jan_final_iv_curve.expiry: expected_jan_final_iv_curve,
            expected_feb_final_iv_curve.expiry: expected_feb_final_iv_curve,
        },
    )


@pytest.fixture
def current_time_supplier(current_time: dt.datetime) -> Mock:
    supplier = Mock(spec_set=AbstractCurrentTimeSupplier)
    supplier.get_current_time.return_value = current_time
    return supplier


@pytest.fixture
def raw_iv_supplier(raw_iv_surface: RawIVSurface) -> Mock:
    supplier = Mock(spec_set=AbstractRawIVSupplier)
    supplier.get_raw_iv_surface.return_value = raw_iv_surface
    return supplier


@pytest.fixture
def forward_curve_supplier(forward_curve: ForwardCurve) -> Mock:
    supplier = Mock(spec_set=AbstractForwardCurveSupplier)
    supplier.get_forward_curve.return_value = forward_curve
    return supplier


@pytest.fixture
def pricing_supplier(pricing: Dict[Option, Pricing]) -> Mock:
    supplier = Mock(spec_set=AbstractPricingSupplier)
    supplier.get_pricing.return_value = pricing
    return supplier


@pytest.fixture
def final_iv_consumer() -> Mock:
    return Mock(spec_set=AbstractFinalIVConsumer)


@pytest.fixture
def volfitter_service(
    volfitter_config: VolfitterConfig,
    current_time_supplier: AbstractCurrentTimeSupplier,
    raw_iv_supplier: AbstractRawIVSupplier,
    forward_curve_supplier: AbstractForwardCurveSupplier,
    pricing_supplier: AbstractPricingSupplier,
    final_iv_consumer: AbstractFinalIVConsumer,
) -> VolfitterService:
    return create_volfitter_service_from_adaptors(
        volfitter_config,
        current_time_supplier,
        raw_iv_supplier,
        forward_curve_supplier,
        pricing_supplier,
        final_iv_consumer,
    )


def test_fits_final_surface_from_raw_surface(
    volfitter_service: VolfitterService,
    final_iv_consumer: Mock,
    expected_final_iv_surface: FinalIVSurface,
):
    volfitter_service.fit_full_surface()

    assert_surface_approx_equal(
        final_iv_consumer.consume_final_iv_surface.call_args.args[0],
        expected_final_iv_surface,
    )
