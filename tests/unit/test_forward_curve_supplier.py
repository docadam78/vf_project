import datetime as dt
import pandas as pd

from unittest.mock import Mock

from volfitter.adapters.forward_curve_supplier import OptionMetricsForwardCurveSupplier
from volfitter.adapters.sample_data_loader import AbstractDataFrameSupplier
from volfitter.domain.datamodel import ForwardCurve


def test_option_metrics_forward_curve_supplier_correctly_constructs_forward_curve_from_data_frame():
    datetime = dt.datetime(2022, 1, 1, 12, 0)

    columns = [
        "expiration",
        "AMSettlement",
        "ForwardPrice",
    ]
    data = [
        (20200101, 0, 100),
        (20200201, 0, 105),
        (20200301, 1, 109),
        (20200301, 0, 110),
    ]

    df = pd.DataFrame.from_records(data, columns=columns)

    expected_expiry_1 = dt.datetime(2020, 1, 1, 15, 0)
    expected_expiry_2 = dt.datetime(2020, 2, 1, 15, 0)
    expected_expiry_3 = dt.datetime(2020, 3, 1, 8, 30)
    expected_expiry_4 = dt.datetime(2020, 3, 1, 15, 0)

    expected_forward_curve = ForwardCurve(
        datetime,
        {
            expected_expiry_1: 100,
            expected_expiry_2: 105,
            expected_expiry_3: 109,
            expected_expiry_4: 110,
        },
    )

    data_frame_supplier = _create_data_frame_supplier(df)
    victim = OptionMetricsForwardCurveSupplier(data_frame_supplier)

    forward_curve = victim.get_forward_curve(datetime)

    data_frame_supplier.get_dataframe.assert_called_once_with(datetime)
    assert forward_curve == expected_forward_curve


def _create_data_frame_supplier(data_frame: pd.DataFrame) -> Mock:
    data_frame_supplier = Mock(spec_set=AbstractDataFrameSupplier)
    data_frame_supplier.get_dataframe.return_value = data_frame
    return data_frame_supplier
