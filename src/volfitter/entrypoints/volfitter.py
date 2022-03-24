"""
Module containing the main entrypoint to start and run the application.
"""

import datetime as dt
import logging
import tzlocal

from apscheduler.schedulers.blocking import BlockingScheduler

from volfitter.composition_root import create_volfitter_service
from volfitter.config import VolfitterConfig


def run():
    """
    Starts and runs the volfitter application.

    This method instantiates the VolfitterService and starts a timer which
    repeatedly triggers the orchestration logic within the service layer.
    """

    volfitter_config = VolfitterConfig.from_environ()
    logging.basicConfig(
        filename=volfitter_config.log_file,
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
        filemode="w",
        level=logging.INFO,
    )
    logging.captureWarnings(True)

    volfitter_service = create_volfitter_service(volfitter_config)

    def volfitter_job():
        volfitter_service.fit_full_surface()

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
