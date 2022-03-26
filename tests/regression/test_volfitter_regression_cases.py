import pickle
from pathlib import Path
from typing import Tuple

from tests.regression.regression_test_adapters import RegressionTestAdapter
from volfitter.config import VolfitterConfig
from volfitter.domain.datamodel import FinalIVSurface


def case_amzn_20200110_before_covid_bear_market() -> Tuple[
    VolfitterConfig, RegressionTestAdapter, FinalIVSurface
]:
    return _load_regression_test_data("AMZN", "20200110")


def case_amzn_20200312_covid_black_thursday() -> Tuple[
    VolfitterConfig, RegressionTestAdapter, FinalIVSurface
]:
    return _load_regression_test_data("AMZN", "20200312")


def _load_regression_test_data(
    symbol: str, date: str
) -> Tuple[VolfitterConfig, RegressionTestAdapter, FinalIVSurface]:
    filename = f"{Path(__file__).parent}/data/{symbol}/{date}_{symbol}_regression_test_data.pickle"
    with open(filename, "rb") as file:
        (
            volfitter_config,
            current_time,
            raw_iv_surface,
            forward_curve,
            pricing,
            expected_final_iv_surface,
        ) = pickle.load(file)

    regression_test_adapter = RegressionTestAdapter(
        current_time, raw_iv_surface, forward_curve, pricing
    )

    return volfitter_config, regression_test_adapter, expected_final_iv_surface
