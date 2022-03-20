"""
Module containing runtime configuration classes.

The configuration defined in this module will be read from the process' environment
variables at runtime. Default values are provided, but will be overriden by any
of the relevant env vars if they are set.
"""

import environ

from enum import Enum


class VolfitterMode(Enum):
    BACKTEST = "BACKTEST"
    LIVE = "LIVE"
    SAMPLE_DATA = "SAMPLE_DATA"


@environ.config(prefix="VOLFITTER")
class VolfitterConfig:
    symbol = environ.var(default="AMZN", help="The underlying symbol.")
    volfitter_mode = environ.var(
        default=VolfitterMode.SAMPLE_DATA,
        converter=VolfitterMode,
        help="Mode in which to run the volfitter.",
    )
    log_file = environ.var(default="logs/volfitter.log", help="The log file.")
    fit_interval_s = environ.var(
        default=10, converter=int, help="Fit interval in seconds."
    )

    @environ.config
    class SampleDataConfig:
        input_data_path = environ.var(default="data/input", help="The input data path.")
        input_filename = environ.var(
            default="amzn_option_data_jan2020.csv", help="The input filename."
        )
        output_data_path = environ.var(
            default="data/output", help="The output data path."
        )
        output_filename = environ.var(
            default="final_iv_surface.pickle", help="The output filename."
        )

    sample_data_config = environ.group(SampleDataConfig, optional=True)
