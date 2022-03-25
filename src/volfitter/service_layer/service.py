"""
Module containing the service layer orchestration logic.

The logic in this module defines the use cases of the system.
"""

import datetime as dt
import logging
from typing import Collection

from volfitter.adapters.current_time_supplier import AbstractCurrentTimeSupplier
from volfitter.adapters.final_iv_consumer import AbstractFinalIVConsumer
from volfitter.adapters.forward_curve_supplier import AbstractForwardCurveSupplier
from volfitter.adapters.pricing_supplier import AbstractPricingSupplier
from volfitter.adapters.raw_iv_supplier import AbstractRawIVSupplier
from volfitter.domain.datamodel import RawIVSurface, Option
from volfitter.domain.final_iv_validation import AbstractFinalIVValidator
from volfitter.domain.fitter import AbstractSurfaceFitter
from volfitter.domain.raw_iv_filtering import AbstractRawIVFilter

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
        raw_iv_filter: AbstractRawIVFilter,
        surface_fitter: AbstractSurfaceFitter,
        final_iv_validator: AbstractFinalIVValidator,
        final_iv_consumer: AbstractFinalIVConsumer,
    ):
        self.current_time_supplier = current_time_supplier
        self.raw_iv_supplier = raw_iv_supplier
        self.forward_curve_supplier = forward_curve_supplier
        self.pricing_supplier = pricing_supplier
        self.raw_iv_filter = raw_iv_filter
        self.surface_fitter = surface_fitter
        self.final_iv_validator = final_iv_validator
        self.final_iv_consumer = final_iv_consumer

    def fit_full_surface(self) -> None:
        """
        Fits a full final IV surface.

        Grabs the latest raw IV surface, passes it through the fitter, and passes the
        result to the final IV surface consumer. Performs input filtering and output
        validation.
        """
        current_time = self.current_time_supplier.get_current_time()
        _LOGGER.info(f"Starting run for {current_time}")

        raw_iv_surface = self.raw_iv_supplier.get_raw_iv_surface(current_time)
        expiries = self._get_expiries(raw_iv_surface)
        options = self._get_options(raw_iv_surface)

        forward_curve = self.forward_curve_supplier.get_forward_curve(
            current_time, expiries
        )
        pricing = self.pricing_supplier.get_pricing(
            current_time, forward_curve, options
        )

        filtered_raw_iv_surface = self.raw_iv_filter.filter_raw_ivs(
            raw_iv_surface, pricing
        )
        final_iv_surface = self.surface_fitter.fit_surface_model(
            filtered_raw_iv_surface, pricing
        )
        validated_final_iv_surface = self.final_iv_validator.validate_final_ivs(
            final_iv_surface, raw_iv_surface, pricing
        )

        self.final_iv_consumer.consume_final_iv_surface(validated_final_iv_surface)

    def _get_expiries(self, raw_iv_surface: RawIVSurface) -> Collection[dt.datetime]:
        return set(raw_iv_surface.curves.keys())

    def _get_options(self, raw_iv_surface: RawIVSurface) -> Collection[Option]:
        return set().union(
            *[set(curve.points.keys()) for curve in raw_iv_surface.curves.values()]
        )
