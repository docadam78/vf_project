"""
Module containing the main entrypoint to start and run the application.
"""

import datetime as dt
import logging
import os
import tzlocal

from apscheduler.schedulers.blocking import BlockingScheduler

from volfitter.adapters.current_time_supplier import (
    create_cycling_current_time_supplier,
)
from volfitter.adapters.final_iv_consumer import PickleFinalIVConsumer
from volfitter.adapters.raw_iv_supplier import OptionMetricsRawIVSupplier
from volfitter.adapters.sample_data_loader import (
    CachingDataFrameSupplier,
    OptionDataFrameLoader,
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
    logging.basicConfig(
        filename=volfitter_config.log_file,
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
        filemode="w",
        level=logging.INFO,
    )

    if volfitter_config.volfitter_mode != VolfitterMode.SAMPLE_DATA:
        raise ValueError(f"{volfitter_config.volfitter_mode} not currently supported.")

    option_dataframe_loader = OptionDataFrameLoader(
        volfitter_config.symbol, volfitter_config.sample_data_config
    )
    caching_option_dataframe_supplier = CachingDataFrameSupplier(
        option_dataframe_loader
    )

    current_time_supplier = create_cycling_current_time_supplier(
        caching_option_dataframe_supplier
    )
    raw_iv_supplier = OptionMetricsRawIVSupplier(caching_option_dataframe_supplier)

    fitter = PassThroughSurfaceFitter()

    output_file = _ensure_output_data_path(volfitter_config)
    final_iv_consumer = PickleFinalIVConsumer(output_file)

    service = VolfitterService(
        current_time_supplier, raw_iv_supplier, fitter, final_iv_consumer
    )

    def volfitter_job():
        service.fit_full_surface()

    scheduler = BlockingScheduler(
        job_defaults={"coalesce": True, "max_instances": 1},
        timezone=str(tzlocal.get_localzone()),
    )
    scheduler.add_job(
        volfitter_job,
        "interval",
        seconds=volfitter_config.fit_interval_s,
        next_run_time=dt.datetime.now(),
    )
    scheduler.start()


def _ensure_output_data_path(volfitter_config: VolfitterConfig) -> str:
    symbol = volfitter_config.symbol
    sample_data_config = volfitter_config.sample_data_config

    output_data_path = f"{sample_data_config.output_data_path}/{symbol}"

    if not os.path.exists(output_data_path):
        os.makedirs(output_data_path)

    return f"{output_data_path}/{sample_data_config.output_filename}"
