"""
Module containing the service layer orchestration logic.

The logic in this module defines the use cases of the system.
"""

import logging
from typing import Collection

from volfitter.adapters.current_time_supplier import AbstractCurrentTimeSupplier
from volfitter.adapters.final_iv_consumer import AbstractFinalIVConsumer
from volfitter.adapters.forward_curve_supplier import AbstractForwardCurveSupplier
from volfitter.adapters.pricing_supplier import AbstractPricingSupplier
from volfitter.adapters.raw_iv_supplier import AbstractRawIVSupplier
from volfitter.domain.datamodel import RawIVSurface, Option
from volfitter.domain.fitter import AbstractSurfaceFitter


_LOGGER = logging.getLogger(__name__)


class VolfitterService:
    """
    Orchestrates the components of the system and defines the use cases.
    """

    def __init__(
        self,
        current_time_supplier: AbstractCurrentTimeSupplier,
        raw_iv_supplier: AbstractRawIVSupplier,
        forward_curve_supplier: AbstractForwardCurveSupplier,
        pricing_supplier: AbstractPricingSupplier,
        surface_fitter: AbstractSurfaceFitter,
        final_iv_consumer: AbstractFinalIVConsumer,
    ):
        self.current_time_supplier = current_time_supplier
        self.raw_iv_supplier = raw_iv_supplier
        self.forward_curve_supplier = forward_curve_supplier
        self.pricing_supplier = pricing_supplier
        self.surface_fitter = surface_fitter
        self.final_iv_consumer = final_iv_consumer

    def fit_full_surface(self) -> None:
        """
        Fits a full final IV surface.

        Grabs the latest raw IV surface, passes it through the fitter, and passes the
        result to the final IV surface consumer.
        """
        current_time = self.current_time_supplier.get_current_time()
        _LOGGER.info(f"Starting run for {current_time}")

        raw_iv_surface = self.raw_iv_supplier.get_raw_iv_surface(current_time)
        options = self._get_options(raw_iv_surface)

        forward_curve = self.forward_curve_supplier.get_forward_curve(current_time)
        pricing = self.pricing_supplier.get_pricing(
            current_time, forward_curve, options
        )

        final_iv_surface = self.surface_fitter.fit_surface_model(raw_iv_surface)

        self.final_iv_consumer.consume_final_iv_surface(final_iv_surface)

    def _get_options(self, raw_iv_surface: RawIVSurface) -> Collection[Option]:
        return set().union(
            *[set(curve.points.keys()) for curve in raw_iv_surface.curves.values()]
        )
