import datetime as dt

from unittest.mock import Mock

import pytest

from volfitter.adapters.current_time_supplier import AbstractCurrentTimeSupplier
from volfitter.adapters.final_iv_consumer import AbstractFinalIVConsumer
from volfitter.adapters.forward_curve_supplier import AbstractForwardCurveSupplier
from volfitter.adapters.raw_iv_supplier import AbstractRawIVSupplier
from volfitter.domain.datamodel import FinalIVSurface, RawIVSurface
from volfitter.domain.fitter import AbstractSurfaceFitter
from volfitter.service_layer.service import VolfitterService


@pytest.fixture
def raw_iv_surface(current_time: dt.datetime) -> RawIVSurface:
    return RawIVSurface(current_time, {})


@pytest.fixture
def final_iv_surface(current_time: dt.datetime) -> FinalIVSurface:
    return FinalIVSurface(current_time, {})


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
def forward_curve_supplier() -> Mock:
    return Mock(spec_set=AbstractForwardCurveSupplier)


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
    raw_iv_surface: RawIVSurface,
    final_iv_surface: FinalIVSurface,
    current_time_supplier: AbstractCurrentTimeSupplier,
    raw_iv_supplier: Mock,
    forward_curve_supplier: Mock,
    surface_fitter: Mock,
    final_iv_consumer: Mock,
):
    victim = VolfitterService(
        current_time_supplier,
        raw_iv_supplier,
        forward_curve_supplier,
        surface_fitter,
        final_iv_consumer,
    )

    victim.fit_full_surface()

    raw_iv_supplier.get_raw_iv_surface.assert_called_once_with(current_time)
    forward_curve_supplier.get_forward_curve.assert_called_once_with(current_time)
    surface_fitter.fit_surface_model.assert_called_once_with(raw_iv_surface)
    final_iv_consumer.consume_final_iv_surface.assert_called_once_with(final_iv_surface)
