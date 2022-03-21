"""
Module containing current time suppliers.

When running "live," the current time is just the current system time. However,
additional functionality is needed to support "backtest" and "sample data" modes. In
modes such as those, the "current time" actually needs to be the time corresponding
to when the input data was generated, not the time the fitter happens to run.
"""

import abc
import datetime as dt

from typing import List

from volfitter.adapters.sample_data_loader import AbstractDataFrameSupplier


class AbstractCurrentTimeSupplier(abc.ABC):
    """
    Abstract base class for current time suppliers.
    """

    @abc.abstractmethod
    def get_current_time(self) -> dt.datetime:
        """
        Returns the current time that the fitter should use.
        :return: The current time for the fitter.
        """
        raise NotImplementedError


class CyclingCurrentTimeSupplier(AbstractCurrentTimeSupplier):
    """
    Cycles through a pre-supplied list of "current times."

    Returns each one as the current time upon successive calls. Loops back to the
    start of the list upon reaching the end.
    """

    def __init__(self, times: List[dt.datetime]):
        self.times = times
        self.next_time_index = 0

    def get_current_time(self) -> dt.datetime:
        """
        Returns the next time in the pre-supplied list as the "current time."
        :return: Pre-supplied "current time."
        """
        time = self.times[self.next_time_index]

        self.next_time_index += 1
        if self.next_time_index >= len(self.times):
            self.next_time_index = 0

        return time


def create_cycling_current_time_supplier(
    dataframe_supplier: AbstractDataFrameSupplier,
) -> CyclingCurrentTimeSupplier:
    """
    Creates a CyclingCurrentTimeSupplier using the dates in a DataFrame.

    Assumes each datetime will be at 15:00 on the given date (i.e., market close in the
    Central timezone).

    :param dataframe_supplier: The DataFrameSupplier.
    :return: CyclingCurrentTimeSupplier with dates from the supplied DataFrame.
    """
    df = dataframe_supplier.get_full_dataframe()

    times = [
        dt.datetime.strptime(str(date), "%Y%m%d").replace(hour=15, minute=0)
        for date in df["date"].unique()
    ]

    return CyclingCurrentTimeSupplier(times)
