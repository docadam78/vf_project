"""
Module instantiating and wiring together the components of our application.

This module performs the Dependency Injection (DI) in our application. It is the sole
place where the structure of the dependency graph is defined. Concrete implementations
of the various abstract dependencies are instantiated and wired together, possibly
based on configuration.
"""

import os

from typing import Tuple

from volfitter.adapters.current_time_supplier import (
    AbstractCurrentTimeSupplier,
    create_cycling_current_time_supplier,
)
from volfitter.adapters.final_iv_consumer import (
    AbstractFinalIVConsumer,
    PickleFinalIVConsumer,
)
from volfitter.adapters.forward_curve_supplier import (
    AbstractForwardCurveSupplier,
    OptionMetricsForwardCurveSupplier,
)
from volfitter.adapters.pricing_supplier import (
    AbstractPricingSupplier,
    OptionMetricsPricingSupplier,
)
from volfitter.adapters.raw_iv_supplier import (
    AbstractRawIVSupplier,
    OptionMetricsRawIVSupplier,
)
from volfitter.adapters.sample_data_loader import (
    ConcatenatingDataFrameLoader,
    CachingDataFrameSupplier,
)
from volfitter.config import VolfitterConfig, VolfitterMode
from volfitter.domain.fitter import PassThroughSurfaceFitter
from volfitter.domain.raw_iv_filtering import (
    CompositeRawIVFilter,
    InTheMoneyFilter,
    NonTwoSidedMarketFilter,
    InsufficientValidStrikesFilter,
    StaleLastTradeDateFilter,
    WideMarketFilter,
)
from volfitter.service_layer.service import VolfitterService


def create_volfitter_service(volfitter_config: VolfitterConfig) -> VolfitterService:
    """
    Creates a VolfitterService based on the provided VolfitterConfig.

    The VolfitterConfig includes a VolfitterMode, which determines which implementations
    of the adaptors to the outside world are used. Currently the only supported mode is
    "SAMPLE_DATA." Supporting additional modes (e.g. "live" or "backtest") would simply
    be a matter of writing the adaptors.

    :param volfitter_config: The VolfitterConfig.
    :return: The fully constructed VolfitterService.
    """

    if volfitter_config.volfitter_mode == VolfitterMode.SAMPLE_DATA:
        (
            current_time_supplier,
            raw_iv_supplier,
            forward_curve_supplier,
            pricing_supplier,
            final_iv_consumer,
        ) = _create_sample_data_adaptors(volfitter_config)
    else:
        raise ValueError(f"{volfitter_config.volfitter_mode} not currently supported.")

    return create_volfitter_service_from_adaptors(
        volfitter_config,
        current_time_supplier,
        raw_iv_supplier,
        forward_curve_supplier,
        pricing_supplier,
        final_iv_consumer,
    )


def create_volfitter_service_from_adaptors(
    volfitter_config: VolfitterConfig,
    current_time_supplier: AbstractCurrentTimeSupplier,
    raw_iv_supplier: AbstractRawIVSupplier,
    forward_curve_supplier: AbstractForwardCurveSupplier,
    pricing_supplier: AbstractPricingSupplier,
    final_iv_consumer: AbstractFinalIVConsumer,
) -> VolfitterService:
    """
    Creates a VolfitterService from the supplied adaptors.

    :param current_time_supplier: AbstractCurrentTimeSupplier.
    :param raw_iv_supplier: AbstractRawIVSupplier.
    :param forward_curve_supplier: AbstractForwardCurveSupplier.
    :param pricing_supplier: AbstractPricingSupplier.
    :param final_iv_consumer: AbstractFinalIVConsumer.
    :return: VolfitterService.
    """

    raw_iv_filtering_config = volfitter_config.raw_iv_filtering_config
    raw_iv_filter = CompositeRawIVFilter(
        [
            InTheMoneyFilter(),
            NonTwoSidedMarketFilter(),
            StaleLastTradeDateFilter(raw_iv_filtering_config),
            WideMarketFilter(raw_iv_filtering_config),
            InsufficientValidStrikesFilter(raw_iv_filtering_config),
        ]
    )
    fitter = PassThroughSurfaceFitter()

    return VolfitterService(
        current_time_supplier,
        raw_iv_supplier,
        forward_curve_supplier,
        pricing_supplier,
        raw_iv_filter,
        fitter,
        final_iv_consumer,
    )


def _create_sample_data_adaptors(
    volfitter_config: VolfitterConfig,
) -> Tuple[
    AbstractCurrentTimeSupplier,
    AbstractRawIVSupplier,
    AbstractForwardCurveSupplier,
    AbstractPricingSupplier,
    AbstractFinalIVConsumer,
]:
    """
    Creates sample data adaptors reading from and writing to disc.
    :param volfitter_config: VolfitterConfig.
    :return: Tuple[
        AbstractCurrentTimeSupplier,
        AbstractRawIVSupplier,
        AbstractForwardCurveSupplier,
        AbstractPricingSupplier,
        AbstractFinalIVConsumer
    ]
    """
    sample_data_config = volfitter_config.sample_data_config

    option_dataframe_loader = ConcatenatingDataFrameLoader(
        volfitter_config.symbol,
        sample_data_config.input_data_path,
        sample_data_config.option_data_file_substring,
    )
    caching_option_dataframe_supplier = CachingDataFrameSupplier(
        option_dataframe_loader
    )

    current_time_supplier = create_cycling_current_time_supplier(
        caching_option_dataframe_supplier
    )
    raw_iv_supplier = OptionMetricsRawIVSupplier(caching_option_dataframe_supplier)

    forward_dataframe_loader = ConcatenatingDataFrameLoader(
        volfitter_config.symbol,
        sample_data_config.input_data_path,
        sample_data_config.forward_data_file_substring,
    )
    caching_forward_dataframe_supplier = CachingDataFrameSupplier(
        forward_dataframe_loader
    )
    forward_curve_supplier = OptionMetricsForwardCurveSupplier(
        caching_forward_dataframe_supplier
    )

    pricing_supplier = OptionMetricsPricingSupplier(caching_option_dataframe_supplier)

    output_file = _ensure_output_data_path(volfitter_config)
    final_iv_consumer = PickleFinalIVConsumer(output_file)

    return (
        current_time_supplier,
        raw_iv_supplier,
        forward_curve_supplier,
        pricing_supplier,
        final_iv_consumer,
    )


def _ensure_output_data_path(volfitter_config: VolfitterConfig) -> str:
    symbol = volfitter_config.symbol
    sample_data_config = volfitter_config.sample_data_config

    output_data_path = f"{sample_data_config.output_data_path}/{symbol}"

    if not os.path.exists(output_data_path):
        os.makedirs(output_data_path)

    return f"{output_data_path}/{sample_data_config.output_filename}"
