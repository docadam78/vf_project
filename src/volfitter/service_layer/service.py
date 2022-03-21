"""
Module containing the service layer orchestration logic.

The logic in this module defines the use cases of the system.
"""

import logging

from volfitter.adapters.current_time_supplier import AbstractCurrentTimeSupplier
from volfitter.adapters.final_iv_consumer import AbstractFinalIVConsumer
from volfitter.adapters.raw_iv_supplier import AbstractRawIVSupplier
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
        surface_fitter: AbstractSurfaceFitter,
        final_iv_consumer: AbstractFinalIVConsumer,
    ):
        self.current_time_supplier = current_time_supplier
        self.raw_iv_supplier = raw_iv_supplier
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
        final_iv_surface = self.surface_fitter.fit_surface_model(raw_iv_surface)
        self.final_iv_consumer.consume_final_iv_surface(final_iv_surface)
