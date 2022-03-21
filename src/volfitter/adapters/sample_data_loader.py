"""
Module for loading sample input data.

The loading code in this module is intended to be used by adapters which translate the
sample input data into the format expected by the rest of the application.
"""

import abc
import datetime as dt
import os
import pandas as pd

from volfitter.config.config import VolfitterConfig


class AbstractDataFrameSupplier(abc.ABC):
    """
    Abstract base class for DataFrame suppliers.

    Used internally to classes which read sample input data from Pandas DataFrames.
    """

    @abc.abstractmethod
    def get_dataframe(self, datetime: dt.datetime) -> pd.DataFrame:
        """
        Returns a DataFrame for a given datetime.

        :param datetime: The datetime for which a DataFrame should be returned.
        :return: The DataFrame.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_full_dataframe(self) -> pd.DataFrame:
        """
        Returns a full DataFrame, not restricted by datetime.
        :return: The DataFrame.
        """
        raise NotImplementedError


class AbstractDataFrameLoader(abc.ABC):
    """
    Abstract base class for DataFrame loaders.
    """

    @abc.abstractmethod
    def load_dataframe(self) -> pd.DataFrame:
        """
        Loads a DataFrame from disc.
        :return: DataFrame.
        """
        raise NotImplementedError


class OptionDataFrameLoader(AbstractDataFrameLoader):
    """
    Loads options DataFrame from disc.
    """

    def __init__(
        self, symbol: str, sample_data_config: VolfitterConfig.SampleDataConfig
    ):
        self.symbol = symbol
        self.sample_data_config = sample_data_config

    def load_dataframe(self) -> pd.DataFrame:
        """
        Loads a single DataFrame based on SampleDataConfig.

        Concatenates a single DataFrame from all the relevant files specified in the
        configuration.
        :return: DataFrame.
        """
        directory = f"{self.sample_data_config.input_data_path}/{self.symbol}"
        files = sorted(
            [
                f"{directory}/{file}"
                for file in os.listdir(directory)
                if self.sample_data_config.option_data_file_substring in file
            ]
        )
        dfs = [pd.read_csv(file) for file in files]
        return pd.concat(dfs)


class CachingDataFrameSupplier(AbstractDataFrameSupplier):
    """
    DataFrameSupplier with caching.
    """

    def __init__(self, dataframe_loader: AbstractDataFrameLoader):
        self.dataframe_loader = dataframe_loader
        self.dataframe = None

    def get_dataframe(self, datetime: dt.datetime) -> pd.DataFrame:
        """
        Returns the DataFrame corresponding to the supplied datetime.
        :param datetime: The datetime.
        :return: The DataFrame.
        """
        date = int(datetime.strftime("%Y%m%d"))
        full_df = self.get_full_dataframe()
        return full_df[full_df["date"] == date]

    def get_full_dataframe(self) -> pd.DataFrame:
        """
        Returns the full DataFrame, caching it for subsequent calls.
        :return: The full DataFrame.
        """
        if self.dataframe is None:
            self.dataframe = self.dataframe_loader.load_dataframe()

        return self.dataframe
