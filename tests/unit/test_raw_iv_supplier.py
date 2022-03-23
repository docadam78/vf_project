import datetime as dt
import numpy as np
import pandas as pd

from unittest.mock import Mock
from volfitter.adapters.raw_iv_supplier import (
    OptionMetricsRawIVSupplier,
    AbstractDataFrameSupplier,
)
from volfitter.domain.datamodel import (
    RawIVSurface,
    RawIVCurve,
    Option,
    OptionKind,
    ExerciseStyle,
    RawIVPoint,
    ok,
)


def test_option_metrics_raw_iv_supplier_correctly_constructs_raw_iv_surface_from_data_frame():
    datetime = dt.datetime(2022, 1, 1, 12, 0)

    columns = [
        "symbol",
        "exdate",
        "am_settlement",
        "strike_price",
        "cp_flag",
        "exercise_style",
        "contract_size",
        "last_date",
        "best_bid",
        "best_offer",
        "impl_volatility",
        "vega",
    ]
    data = [
        (
            "AMZN foo",
            20200101,
            0,
            100000,
            "C",
            "A",
            100,
            20200102.0,
            9.5,
            10.5,
            0.16,
            50,
        ),
        (
            "AMZN bar",
            20200101,
            0,
            100000,
            "P",
            "A",
            100,
            20200103.0,
            9.0,
            10.0,
            0.17,
            60,
        ),
        (
            "AMZN baz",
            20200101,
            1,
            200000,
            "C",
            "A",
            100,
            20200104.0,
            10.5,
            11.5,
            0.18,
            70,
        ),
        ("AMZN qux", 20200201, 0, 300000, "C", "E", 100, np.nan, 8.5, 9.5, 0.19, 80),
    ]
    df = pd.DataFrame.from_records(data, columns=columns)

    expected_expiry_1 = dt.datetime(2020, 1, 1, 15, 0)
    expected_expiry_2 = dt.datetime(2020, 1, 1, 8, 30)
    expected_expiry_3 = dt.datetime(2020, 2, 1, 15, 0)

    expected_option_1 = Option(
        "AMZN", expected_expiry_1, 100, OptionKind.CALL, ExerciseStyle.AMERICAN, 100
    )
    expected_option_2 = Option(
        "AMZN", expected_expiry_1, 100, OptionKind.PUT, ExerciseStyle.AMERICAN, 100
    )
    expected_option_3 = Option(
        "AMZN", expected_expiry_2, 200, OptionKind.CALL, ExerciseStyle.AMERICAN, 100
    )
    expected_option_4 = Option(
        "AMZN", expected_expiry_3, 300, OptionKind.CALL, ExerciseStyle.EUROPEAN, 100
    )

    expected_raw_iv_surface = RawIVSurface(
        datetime,
        {
            expected_expiry_1: RawIVCurve(
                expected_expiry_1,
                ok(),
                {
                    expected_option_1: RawIVPoint(
                        expected_option_1,
                        dt.date(2020, 1, 2),
                        0.16 - 0.5 * 1 / 50,
                        0.16 + 0.5 * 1 / 50,
                    ),
                    expected_option_2: RawIVPoint(
                        expected_option_2,
                        dt.date(2020, 1, 3),
                        0.17 - 0.5 * 1 / 60,
                        0.17 + 0.5 * 1 / 60,
                    ),
                },
            ),
            expected_expiry_2: RawIVCurve(
                expected_expiry_2,
                ok(),
                {
                    expected_option_3: RawIVPoint(
                        expected_option_3,
                        dt.date(2020, 1, 4),
                        0.18 - 0.5 * 1 / 70,
                        0.18 + 0.5 * 1 / 70,
                    )
                },
            ),
            expected_expiry_3: RawIVCurve(
                expected_expiry_3,
                ok(),
                {
                    expected_option_4: RawIVPoint(
                        expected_option_4,
                        dt.date(1970, 1, 1),
                        0.19 - 0.5 * 1 / 80,
                        0.19 + 0.5 * 1 / 80,
                    )
                },
            ),
        },
    )

    data_frame_supplier = _create_data_frame_supplier(df)
    victim = OptionMetricsRawIVSupplier(data_frame_supplier)

    raw_iv_surface = victim.get_raw_iv_surface(datetime)

    data_frame_supplier.get_dataframe.assert_called_once_with(datetime)
    assert raw_iv_surface == expected_raw_iv_surface


def _create_data_frame_supplier(data_frame: pd.DataFrame) -> Mock:
    data_frame_supplier = Mock(spec_set=AbstractDataFrameSupplier)
    data_frame_supplier.get_dataframe.return_value = data_frame
    return data_frame_supplier
