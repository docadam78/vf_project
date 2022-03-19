from unittest.mock import Mock

from volfitter.adapters.final_iv_consumer import AbstractFinalIVConsumer
from volfitter.adapters.raw_iv_supplier import AbstractRawIVSupplier
from volfitter.domain.datamodel import FinalIVSurface, RawIVSurface
from volfitter.domain.fitter import AbstractSurfaceFitter
from volfitter.service_layer.service import VolfitterService


def test_volfitter_service_passes_raw_surface_through_fitter_to_consumer():
    raw_iv_surface = RawIVSurface({})
    final_iv_surface = FinalIVSurface({})

    raw_iv_supplier = _create_raw_iv_supplier(raw_iv_surface)
    surface_fitter = _create_surface_fitter(final_iv_surface)
    final_iv_consumer = _create_final_iv_consumer()

    victim = VolfitterService(raw_iv_supplier, surface_fitter, final_iv_consumer)

    victim.fit_full_surface()

    surface_fitter.fit_surface_model.assert_called_once_with(raw_iv_surface)
    final_iv_consumer.consume_final_iv_surface.assert_called_once_with(final_iv_surface)


def _create_raw_iv_supplier(raw_iv_surface: RawIVSurface) -> Mock:
    raw_iv_supplier = Mock(spec_set=AbstractRawIVSupplier)
    raw_iv_supplier.get_raw_iv_surface.return_value = raw_iv_surface
    return raw_iv_supplier


def _create_surface_fitter(final_iv_surface: FinalIVSurface) -> Mock:
    surface_fitter = Mock(spec_set=AbstractSurfaceFitter)
    surface_fitter.fit_surface_model.return_value = final_iv_surface
    return surface_fitter


def _create_final_iv_consumer() -> Mock:
    return Mock(spec_set=AbstractFinalIVConsumer)
