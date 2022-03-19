"""
Module containing the main entrypoint to start and run the application.
"""

import os

from volfitter.adapters.final_iv_consumer import PickleFinalIVConsumer
from volfitter.adapters.raw_iv_supplier import (
    OptionMetricsRawIVSupplier,
    CSVDataFrameSupplier,
)
from volfitter.domain.fitter import PassThroughSurfaceFitter
from volfitter.service_layer.service import VolfitterService


def run():
    """
    Starts and runs the volfitter application.

    This method instantiates concrete implementations of the system's dependencies and
    wires them together to create the VolfitterService. It then calls the orchestration
    logic within the service layer.
    """

    input_data = "data/input/AMZN/amzn_option_data_jan2020.csv"
    output_data_path = "data/output/AMZN"
    output_file = output_data_path + "/final_surface.pickle"

    if not os.path.exists(output_data_path):
        os.makedirs(output_data_path)

    raw_iv_supplier = OptionMetricsRawIVSupplier(CSVDataFrameSupplier(input_data))
    fitter = PassThroughSurfaceFitter()
    final_iv_consumer = PickleFinalIVConsumer(output_file)

    service = VolfitterService(raw_iv_supplier, fitter, final_iv_consumer)

    service.fit_full_surface()

    print("Run successful.")
