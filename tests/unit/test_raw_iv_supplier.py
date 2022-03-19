import datetime as dt
import pandas as pd

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
)


def test_option_metrics_raw_iv_supplier_correctly_constructs_raw_iv_surface_from_data_frame():
    columns = [
        "symbol",
        "exdate",
        "am_settlement",
        "strike_price",
        "cp_flag",
        "exercise_style",
        "contract_size",
        "best_bid",
        "best_offer",
        "impl_volatility",
        "vega",
    ]
    data = [
        ("AMZN foo", 20200101, 0, 100000, "C", "A", 100, 9.5, 10.5, 0.16, 50),
        ("AMZN bar", 20200101, 0, 100000, "P", "A", 100, 9.0, 10.0, 0.17, 60),
        ("AMZN baz", 20200101, 1, 200000, "C", "A", 100, 10.5, 11.5, 0.18, 70),
        ("AMZN qux", 20200201, 0, 300000, "C", "E", 100, 8.5, 9.5, 0.19, 80),
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
        {
            expected_expiry_1: RawIVCurve(
                expected_expiry_1,
                {
                    expected_option_1: RawIVPoint(
                        expected_option_1, 0.16 - 0.5 * 1 / 50, 0.16 + 0.5 * 1 / 50
                    ),
                    expected_option_2: RawIVPoint(
                        expected_option_2, 0.17 - 0.5 * 1 / 60, 0.17 + 0.5 * 1 / 60
                    ),
                },
            ),
            expected_expiry_2: RawIVCurve(
                expected_expiry_2,
                {
                    expected_option_3: RawIVPoint(
                        expected_option_3, 0.18 - 0.5 * 1 / 70, 0.18 + 0.5 * 1 / 70
                    )
                },
            ),
            expected_expiry_3: RawIVCurve(
                expected_expiry_3,
                {
                    expected_option_4: RawIVPoint(
                        expected_option_4, 0.19 - 0.5 * 1 / 80, 0.19 + 0.5 * 1 / 80
                    )
                },
            ),
        }
    )

    victim = OptionMetricsRawIVSupplier(FakeDataFrameSupplier(df))

    raw_iv_surface = victim.get_raw_iv_surface()

    assert raw_iv_surface == expected_raw_iv_surface


class FakeDataFrameSupplier(AbstractDataFrameSupplier):
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def get_dataframe(self) -> pd.DataFrame:
        return self.df