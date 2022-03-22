import datetime as dt
import math
import pandas as pd

from unittest.mock import Mock

from volfitter.adapters.pricing_supplier import OptionMetricsPricingSupplier
from volfitter.adapters.sample_data_loader import AbstractDataFrameSupplier
from volfitter.domain.datamodel import (
    ForwardCurve,
    Option,
    OptionKind,
    ExerciseStyle,
    Pricing,
)


def test_option_metrics_pricing_supplier_correctly_constructs_pricing_for_requested_options_from_data_frame():
    datetime = dt.datetime(2022, 1, 1, 15, 0)

    columns = [
        "symbol",
        "exdate",
        "am_settlement",
        "strike_price",
        "cp_flag",
        "exercise_style",
        "contract_size",
        "delta",
        "gamma",
        "vega",
        "theta",
    ]
    data = [
        ("AMZN foo", 20220201, 0, 100000, "C", "A", 100, 1, 2, 3, 4),
        ("AMZN bar", 20220201, 0, 100000, "P", "A", 100, 5, 6, 7, 8),
        ("AMZN baz", 20220201, 1, 200000, "C", "A", 100, 9, 10, 11, 12),
        ("AMZN qux", 20220301, 0, 300000, "C", "E", 100, 13, 14, 15, 16),
    ]
    df = pd.DataFrame.from_records(data, columns=columns)

    expiry_1 = dt.datetime(2022, 2, 1, 15, 0)
    expiry_2 = dt.datetime(2022, 2, 1, 8, 30)
    expiry_3 = dt.datetime(2022, 3, 1, 15, 0)

    forward_curve = ForwardCurve(datetime, {expiry_1: 100, expiry_2: 99, expiry_3: 110})

    option_1 = Option(
        "AMZN", expiry_1, 100, OptionKind.CALL, ExerciseStyle.AMERICAN, 100
    )
    option_2 = Option(
        "AMZN", expiry_2, 200, OptionKind.CALL, ExerciseStyle.AMERICAN, 100
    )
    option_3 = Option(
        "AMZN", expiry_3, 300, OptionKind.CALL, ExerciseStyle.EUROPEAN, 100
    )

    expected_pricing = {
        option_1: Pricing(option_1, math.log(100 / 100), 1, 2, 3, 4, 31 / 365),
        option_2: Pricing(
            option_2, math.log(200 / 99), 9, 10, 11, 12, (31 - 6.5 / 24) / 365
        ),
        option_3: Pricing(option_3, math.log(300 / 110), 13, 14, 15, 16, 59 / 365),
    }

    data_frame_supplier = _create_data_frame_supplier(df)
    victim = OptionMetricsPricingSupplier(data_frame_supplier)

    pricing = victim.get_pricing(
        datetime, forward_curve, [option_1, option_2, option_3]
    )

    data_frame_supplier.get_dataframe.assert_called_once_with(datetime)
    assert pricing == expected_pricing


def _create_data_frame_supplier(data_frame: pd.DataFrame) -> Mock:
    data_frame_supplier = Mock(spec_set=AbstractDataFrameSupplier)
    data_frame_supplier.get_dataframe.return_value = data_frame
    return data_frame_supplier
