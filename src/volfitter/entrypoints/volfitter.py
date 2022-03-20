"""
Module containing the main entrypoint to start and run the application.
"""

import os

from volfitter.adapters.final_iv_consumer import PickleFinalIVConsumer
from volfitter.adapters.raw_iv_supplier import (
    OptionMetricsRawIVSupplier,
    CSVDataFrameSupplier,
)
from volfitter.config.config import VolfitterConfig, VolfitterMode
from volfitter.domain.fitter import PassThroughSurfaceFitter
from volfitter.service_layer.service import VolfitterService

def run():
    """
    Starts and runs the volfitter application.

    This method instantiates concrete implementations of the system's dependencies and
    wires them together to create the VolfitterService. It then calls the orchestration
    logic within the service layer.
    """

    volfitter_config = VolfitterConfig.from_environ()
    if volfitter_config.volfitter_mode != VolfitterMode.SAMPLE_DATA:
        raise ValueError(f"{volfitter_config.volfitter_mode} not currently supported.")

    input_file = _format_input_data_path(volfitter_config)
    output_file = _ensure_output_data_path(volfitter_config)

    raw_iv_supplier = OptionMetricsRawIVSupplier(CSVDataFrameSupplier(input_file))
    fitter = PassThroughSurfaceFitter()
    final_iv_consumer = PickleFinalIVConsumer(output_file)

    service = VolfitterService(raw_iv_supplier, fitter, final_iv_consumer)

    service.fit_full_surface()

    print("Run successful.")


def _format_input_data_path(volfitter_config: VolfitterConfig) -> str:
    symbol = volfitter_config.symbol
    sample_data_config = volfitter_config.sample_data_config

    return f"{sample_data_config.input_data_path}/{symbol}/{sample_data_config.input_filename}"


def _ensure_output_data_path(volfitter_config: VolfitterConfig) -> str:
    symbol = volfitter_config.symbol
    sample_data_config = volfitter_config.sample_data_config

    output_data_path = f"{sample_data_config.output_data_path}/{symbol}"

    if not os.path.exists(output_data_path):
        os.makedirs(output_data_path)

    return f"{output_data_path}/{sample_data_config.output_filename}"
