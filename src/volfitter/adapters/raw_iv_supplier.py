"""
Module containing ports and adapters for raw IV suppliers.

Contains both the abstract interface and concrete implementation.
"""

import abc
import datetime as dt
import numpy as np

from typing import List

from volfitter.adapters.option_metrics_helpers import create_option
from volfitter.adapters.sample_data_loader import AbstractDataFrameSupplier
from volfitter.domain.datamodel import (
    RawIVSurface,
    RawIVPoint,
    RawIVCurve,
    ok,
)


class AbstractRawIVSupplier(abc.ABC):
    """
    Abstract base class for raw IV suppliers.
    """

    @abc.abstractmethod
    def get_raw_iv_surface(self, datetime: dt.datetime) -> RawIVSurface:
        """
        Returns a raw IV surface.

        :param datetime: The datetime for which to return a raw IV surface.
        :return: RawIVSurface
        """
        raise NotImplementedError


class OptionMetricsRawIVSupplier(AbstractRawIVSupplier):
    """
    Constructs a RawIVSurface from a DataFrame containing OptionMetrics data.

    OptionMetrics is a vendor supplying historical options data, including best
    bids/offers, implied vols, Greeks, etc. This class expects the input data to be in
    OptionMetrics' format, meaning this class will have to convert it to the format we
    want. For example, they supply "strike price multiplied by 1000" rather than strike
    price, so we have to divide it by 1000.

    See papers/option_metrics_reference_manual.pdf.
    """

    def __init__(self, dataframe_supplier: AbstractDataFrameSupplier):
        self.dataframe_supplier = dataframe_supplier

    def get_raw_iv_surface(self, datetime: dt.datetime) -> RawIVSurface:
        """
        Constructs a RawIVSurface from a DataFrame containing OptionMetrics data.

        :param datetime: The datetime for which to return a raw IV surface.
        :return: RawIVSurface.
        """

        df = self.dataframe_supplier.get_dataframe(datetime)

        # Zipping columns together and iterating over the tuples is far faster than
        # iterating over the dataframe itself.
        rows = zip(
            df["symbol"].values,
            df["exdate"].values,
            df["am_settlement"].values,
            df["strike_price"].values,
            df["cp_flag"].values,
            df["exercise_style"].values,
            df["contract_size"].values,
            df["last_date"].values,
            df["best_bid"].values,
            df["best_offer"].values,
            df["impl_volatility"].values,
            df["vega"].values,
        )

        raw_iv_curves = {}
        for (
            *option_specs,
            last_trade_date,
            bid_price,
            ask_price,
            mid_vol,
            vega,
        ) in rows:
            raw_iv_point = self._create_raw_iv_point(
                option_specs, last_trade_date, bid_price, ask_price, mid_vol, vega
            )
            expiry = raw_iv_point.option.expiry

            if expiry not in raw_iv_curves:
                raw_iv_curves[expiry] = RawIVCurve(expiry, ok(), {})

            raw_iv_curves[expiry].points[raw_iv_point.option] = raw_iv_point

        return RawIVSurface(datetime, raw_iv_curves)

    def _create_raw_iv_point(
        self,
        option_specs: List,
        last_trade_date: float,
        bid_price: float,
        ask_price: float,
        mid_vol: float,
        vega: float,
    ) -> RawIVPoint:
        """
        Creates a RawIVPoint from OptionMetrics data.

        Our vol fitter expects to receive bid and ask vols as input, but OptionMetrics
        supplies only the midpoint vol. However, it also supplies bid and ask prices,
        so we can use these together with vega to approximate the bid and ask vols. This
        approximation will only be good up to first order, meaning in particular it will
        not be accurate for very wide markets, but it should be good enough for our use
        case here in handling sample input data.

        The bid and ask vol can be NaN if any of the inputs are NaN. It is the
        responsibility of downstream consumers of the RawIVPoints to safely handle NaN
        data.

        In particular, the bid vol is explicitly set to NaN if it would be nonpositive,
        as this indicates a valid IV cannot be found.

        :param option_specs: A list of the option contract specs.
        :param last_trade_date: The last trade date of the option in YYYYMMDD format.
            The OptionMetrics data supplies this as a float rather than an int. It
            can be NaN, presumably indicating that the option has never traded (though
            the documentation does not specify this).
        :param bid_price: Best bid price.
        :param ask_price: Best offer price.
        :param mid_vol: Midpoint implied volatility.
        :param vega: Vega.
        :return: RawIVPoint
        """
        price_width = ask_price - bid_price
        vol_width = price_width / vega
        bid_vol = mid_vol - 0.5 * vol_width
        ask_vol = mid_vol + 0.5 * vol_width

        if bid_vol <= 0:
            bid_vol = np.nan

        return RawIVPoint(
            create_option(*option_specs),
            self._create_last_trade_date(last_trade_date),
            bid_vol,
            ask_vol,
        )

    def _create_last_trade_date(self, date: float) -> dt.date:
        """
        Returns a date object representing the given last trade date.

        The last trade date in OptionMetrics data can be NaN. When this happens,
        set it to the Unix epoch, 19700101, indicating that the option has never traded.

        :param date: Last trade date in OptionMetrics format. YYYYMMDD, and can be NaN.
        :return: Last trade date formatted as a date object.
        """

        date_int = 19700101 if np.isnan(date) else int(date)
        return dt.datetime.strptime(str(date_int), "%Y%m%d").date()
