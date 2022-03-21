import datetime as dt
import pandas as pd

from unittest.mock import Mock

from volfitter.adapters.sample_data_loader import (
    AbstractDataFrameLoader,
    CachingDataFrameSupplier,
)


def test_caching_dataframe_supplier_loads_dataframe_only_once():
    dataframe_loader = Mock(spec_set=AbstractDataFrameLoader)
    victim = CachingDataFrameSupplier(dataframe_loader)

    victim.get_full_dataframe()
    victim.get_full_dataframe()

    dataframe_loader.load_dataframe.assert_called_once()


def test_caching_dataframe_supplier_loads_dataframe_only_once_when_selecting_by_date():
    datetime = dt.datetime(2022, 1, 2, 3, 4)
    df = pd.DataFrame(data={"date": [20220102]})

    dataframe_loader = _create_dataframe_loader(df)
    victim = CachingDataFrameSupplier(dataframe_loader)

    victim.get_dataframe(datetime)
    victim.get_dataframe(datetime)

    dataframe_loader.load_dataframe.assert_called_once()


def test_caching_dataframe_supplier_returns_dataframe_for_given_date():
    datetime = dt.datetime(2022, 1, 2, 3, 4)
    df = pd.DataFrame(data={"date": [20220102, 20220102, 20220103]})
    expected_df = pd.DataFrame(data={"date": [20220102, 20220102]})

    dataframe_loader = _create_dataframe_loader(df)
    victim = CachingDataFrameSupplier(dataframe_loader)

    assert victim.get_dataframe(datetime).equals(expected_df)


def _create_dataframe_loader(dataframe: pd.DataFrame) -> Mock:
    dataframe_loader = Mock(spec_set=AbstractDataFrameLoader)
    dataframe_loader.load_dataframe.return_value = dataframe
    return dataframe_loader
