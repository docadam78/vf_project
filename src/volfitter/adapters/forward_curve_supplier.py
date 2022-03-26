"""
Module containing ports and adapters for forward curve suppliers.

Contains both the abstract interface and concrete implementation.
"""

import abc
import datetime as dt
from typing import Collection

from volfitter.adapters.option_metrics_helpers import create_expiry
from volfitter.adapters.sample_data_loader import AbstractDataFrameSupplier
from volfitter.domain.datamodel import ForwardCurve


class AbstractForwardCurveSupplier(abc.ABC):
    """
    Abstract base class for forward curve suppliers.
    """

    @abc.abstractmethod
    def get_forward_curve(
        self, datetime: dt.datetime, expiries: Collection[dt.datetime]
    ) -> ForwardCurve:
        """
        Returns a forward curve.

        :param datetime: The datetime for which to return a forward curve.
        :param expiries: The expiries for which to return forward prices.
        :return: ForwardCurve.
        """
        raise NotImplementedError


class OptionMetricsForwardCurveSupplier(AbstractForwardCurveSupplier):
    """
    Constructs a ForwardCurve from a DataFrame containing OptionMetrics data.

    OptionMetrics is a vendor supplying historical options data. The DataFrame is
    expected to be in their format.

    See papers/option_metrics_reference_manual.pdf.
    """

    def __init__(self, dataframe_supplier: AbstractDataFrameSupplier):
        self.dataframe_supplier = dataframe_supplier

    def get_forward_curve(
        self, datetime: dt.datetime, expiries: Collection[dt.datetime]
    ) -> ForwardCurve:
        """
        Constructs a ForwardCurve from a DataFrame containing OptionMetrics data.

        :param datetime: The datetime for which to return a forward curve.
        :param expiries: The expiries for which to return forward prices.
        :return: ForwardCurve.
        """

        df = self.dataframe_supplier.get_dataframe(datetime)

        rows = zip(
            df["expiration"].values,
            df["AMSettlement"].values,
            df["ForwardPrice"].values,
        )

        all_forward_prices = {
            create_expiry(date, am_settlement): forward
            for (date, am_settlement, forward) in rows
        }

        requested_forward_prices = {}
        for expiry in expiries:
            if expiry not in all_forward_prices:
                raise ValueError(f"Missing forward price for {expiry}!")

            requested_forward_prices[expiry] = all_forward_prices[expiry]

        return ForwardCurve(datetime, requested_forward_prices)
