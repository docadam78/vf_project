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

    @environ.config(prefix="SAMPLE_DATA_CONFIG")
    class SampleDataConfig:
        input_data_path = environ.var(default="data/input", help="The input data path.")
        option_data_file_substring = environ.var(
            default="option_data",
            help="Option data will be loaded from all files in the input directory whose filenames contain this substring.",
        )
        forward_data_file_substring = environ.var(
            default="forward_prices",
            help="Forward prices will be loaded from all files in the input directory whose filenames contain this substring.",
        )
        output_data_path = environ.var(
            default="data/output", help="The output data path."
        )
        output_filename = environ.var(
            default="final_iv_surface.pickle", help="The output filename."
        )

    @environ.config(prefix="RAW_IV_FILTERING_CONFIG")
    class RawIVFilteringConfig:
        min_valid_strikes_fraction = environ.var(
            default=0.1,
            converter=float,
            help="An expiry needs at least this fraction of its strikes to have valid markets in order to be fit.",
        )
        max_last_trade_age_days = environ.var(
            default=3,
            converter=int,
            help="Filter out strikes which have not traded in more than this many business days.",
        )

    sample_data_config = environ.group(SampleDataConfig, optional=True)
    raw_iv_filtering_config = environ.group(RawIVFilteringConfig)
