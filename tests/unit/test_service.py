import datetime as dt
from typing import Dict

from unittest.mock import Mock

import pytest

from volfitter.adapters.current_time_supplier import AbstractCurrentTimeSupplier
from volfitter.adapters.final_iv_consumer import AbstractFinalIVConsumer
from volfitter.adapters.forward_curve_supplier import AbstractForwardCurveSupplier
from volfitter.adapters.pricing_supplier import AbstractPricingSupplier
from volfitter.adapters.raw_iv_supplier import AbstractRawIVSupplier
from volfitter.domain.datamodel import (
    FinalIVSurface,
    RawIVSurface,
    ForwardCurve,
    Option,
    Pricing,
    RawIVCurve,
    RawIVPoint,
    FinalIVCurve,
    FinalIVPoint,
    ok,
)
from volfitter.domain.fitter import AbstractSurfaceFitter
from volfitter.domain.raw_iv_filtering import AbstractRawIVFilter
from volfitter.service_layer.service import VolfitterService


@pytest.fixture
def raw_iv_surface(
    current_time: dt.datetime, jan_expiry: dt.datetime, jan_100_call: Option
) -> RawIVSurface:
    return RawIVSurface(
        current_time,
        {
            jan_expiry: RawIVCurve(
                jan_expiry, ok(), {jan_100_call: RawIVPoint(jan_100_call, 1, 2)}
            )
        },
    )


@pytest.fixture
def filtered_raw_iv_surface(
    current_time: dt.datetime, jan_expiry: dt.datetime, jan_100_call: Option
) -> RawIVSurface:
    return RawIVSurface(
        current_time,
        {
            jan_expiry: RawIVCurve(
                jan_expiry, ok(), {jan_100_call: RawIVPoint(jan_100_call, 3, 4)}
            )
        },
    )


@pytest.fixture
def forward_curve(current_time: dt.datetime, jan_expiry: dt.datetime) -> ForwardCurve:
    return ForwardCurve(current_time, {jan_expiry: 1})


@pytest.fixture
def pricing(jan_100_call: Option) -> Dict[Option, Pricing]:
    return {jan_100_call: Pricing(jan_100_call, 1, 2, 3, 4, 5, 6)}


@pytest.fixture
def final_iv_surface(
    current_time: dt.datetime, jan_expiry: dt.datetime
) -> FinalIVSurface:
    return FinalIVSurface(
        current_time,
        {
            jan_expiry: FinalIVCurve(
                jan_expiry, ok(), {1: FinalIVPoint(jan_expiry, 1, 2)}
            )
        },
    )


@pytest.fixture
def current_time_supplier(current_time: dt.datetime) -> Mock:
    current_time_supplier = Mock(spec_set=AbstractCurrentTimeSupplier)
    current_time_supplier.get_current_time.return_value = current_time
    return current_time_supplier


@pytest.fixture
def raw_iv_supplier(raw_iv_surface: RawIVSurface) -> Mock:
    raw_iv_supplier = Mock(spec_set=AbstractRawIVSupplier)
    raw_iv_supplier.get_raw_iv_surface.return_value = raw_iv_surface
    return raw_iv_supplier


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
def raw_iv_filter(filtered_raw_iv_surface: RawIVSurface) -> Mock:
    filter = Mock(spec_set=AbstractRawIVFilter)
    filter.filter_raw_ivs.return_value = filtered_raw_iv_surface
    return filter


@pytest.fixture
def surface_fitter(final_iv_surface: FinalIVSurface) -> Mock:
    surface_fitter = Mock(spec_set=AbstractSurfaceFitter)
    surface_fitter.fit_surface_model.return_value = final_iv_surface
    return surface_fitter


@pytest.fixture
def final_iv_consumer() -> Mock:
    return Mock(spec_set=AbstractFinalIVConsumer)


def test_volfitter_service_passes_raw_surface_through_fitter_to_consumer(
    current_time: dt.datetime,
    jan_expiry: dt.datetime,
    jan_100_call: Option,
    raw_iv_surface: RawIVSurface,
    forward_curve: ForwardCurve,
    pricing: Dict[Option, Pricing],
    filtered_raw_iv_surface: RawIVSurface,
    final_iv_surface: FinalIVSurface,
    current_time_supplier: AbstractCurrentTimeSupplier,
    raw_iv_supplier: Mock,
    forward_curve_supplier: Mock,
    pricing_supplier: Mock,
    raw_iv_filter: Mock,
    surface_fitter: Mock,
    final_iv_consumer: Mock,
):
    victim = VolfitterService(
        current_time_supplier,
        raw_iv_supplier,
        forward_curve_supplier,
        pricing_supplier,
        raw_iv_filter,
        surface_fitter,
        final_iv_consumer,
    )

    victim.fit_full_surface()

    raw_iv_supplier.get_raw_iv_surface.assert_called_once_with(current_time)
    forward_curve_supplier.get_forward_curve.assert_called_once_with(
        current_time, {jan_expiry}
    )
    pricing_supplier.get_pricing.assert_called_once_with(
        current_time, forward_curve, {jan_100_call}
    )
    raw_iv_filter.filter_raw_ivs.assert_called_once_with(raw_iv_surface, pricing)
    surface_fitter.fit_surface_model.assert_called_once_with(filtered_raw_iv_surface)
    final_iv_consumer.consume_final_iv_surface.assert_called_once_with(final_iv_surface)
