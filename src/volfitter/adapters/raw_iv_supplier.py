"""
Module containing ports and adapters for raw IV suppliers.

Contains both the abstract interface and concrete implementation.
"""

import abc
import datetime as dt
import pandas as pd

from typing import List
from volfitter.domain.datamodel import (
    RawIVSurface,
    Option,
    OptionKind,
    ExerciseStyle,
    RawIVPoint,
    RawIVCurve,
)


class AbstractRawIVSupplier(abc.ABC):
    """
    Abstract base class for raw IV suppliers.
    """

    @abc.abstractmethod
    def get_raw_iv_surface(self) -> RawIVSurface:
        """
        Returns a raw IV surface.
        :return: RawIVSurface
        """
        raise NotImplementedError


class AbstractDataFrameSupplier(abc.ABC):
    """
    Abstract base class for DataFrame suppliers.

    Used internally to classes which read sample input data from Pandas DataFrames.
    """

    @abc.abstractmethod
    def get_dataframe(self) -> pd.DataFrame:
        """
        Returns a DataFrame.
        :return: The DataFrame.
        """
        raise NotImplementedError


class CSVDataFrameSupplier(AbstractDataFrameSupplier):
    """
    Supplies a Pandas DataFrame from a CSV file on disc.
    """

    def __init__(self, filename: str):
        self.filename = filename

    def get_dataframe(self) -> pd.DataFrame:
        """
        Returns the DataFrame read in from the CSV file.
        :return: The DataFrame.
        """
        return pd.read_csv(self.filename)


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

    def __init__(self, data_frame_supplier: AbstractDataFrameSupplier):
        self.data_frame_supplier = data_frame_supplier

    def get_raw_iv_surface(self) -> RawIVSurface:
        """
        Constructs a RawIVSurface from a DataFrame containing OptionMetrics data.
        :return: RawIVSurface.
        """

        df = self.data_frame_supplier.get_dataframe()

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
            df["best_bid"].values,
            df["best_offer"].values,
            df["impl_volatility"].values,
            df["vega"].values,
        )

        raw_iv_curves = {}
        for (*option_specs, bid_price, ask_price, mid_vol, vega) in rows:
            raw_iv_point = self._create_raw_iv_point(
                option_specs, bid_price, ask_price, mid_vol, vega
            )
            expiry = raw_iv_point.option.expiry

            if expiry not in raw_iv_curves:
                raw_iv_curves[expiry] = RawIVCurve(expiry, {})

            raw_iv_curves[expiry].points[raw_iv_point.option] = raw_iv_point

        return RawIVSurface(raw_iv_curves)

    def _create_raw_iv_point(
        self,
        option_specs: List,
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

        :param option_specs: A list of the option contract specs.
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

        return RawIVPoint(self._create_option(*option_specs), bid_vol, ask_vol)

    def _create_option(
        self,
        symbol: str,
        date: int,
        am_settlement: int,
        strike_price: float,
        cp_flag: str,
        exercise_style_flag: str,
        contract_size: int,
    ) -> Option:
        """
        Creates an Option object from data given in the OptionMetrics format.

        :param symbol: A string which contains the underlying symbol before the first
            space. In the OptionMetrics data, the symbol is actually a string
            representation of the option itself, e.g. "AMZN 200101C100000." Here we
            care only about the underlying symbol, "AMZN."
        :param date: The expiry date in YYYYMMDD format.
        :param am_settlement: 1 if expiry is at the open and 0 if expiry is at the
            close.
        :param strike_price: OptionMetrics gives the strike price multiplied by 1000,
            for unknown reasons.
        :param cp_flag: "C" if call, "P" if put.
        :param exercise_style_flag: "A" if American, "E" if European.
        :param contract_size: The contract size.
        :return: An Option object.
        """

        underlying_symbol = symbol.split()[0]
        expiry = self._create_expiry(date, am_settlement)
        strike = strike_price / 1000

        if cp_flag == "C":
            kind = OptionKind.CALL
        elif cp_flag == "P":
            kind = OptionKind.PUT
        else:
            raise ValueError(f"Unsupported cp_flag: {cp_flag}")

        if exercise_style_flag == "A":
            exercise_style = ExerciseStyle.AMERICAN
        elif exercise_style_flag == "E":
            exercise_style = ExerciseStyle.EUROPEAN
        else:
            raise ValueError(f"Unsupported exercise_style: {exercise_style_flag}")

        return Option(
            underlying_symbol,
            expiry,
            strike,
            kind,
            exercise_style,
            contract_size,
        )

    def _create_expiry(self, date: int, am_settlement: int) -> dt.datetime:
        """
        Creates an expiry from date and am_flag, which are in the OptionMetrics format.

        Assumes Central timezone.

        :param date: Date represented as an int in the format YYYYMMDD.
        :param am_settlement: 1 if expiry is at market open, and 0 if expiry is at
            market close.
        :return: A datetime object representing the expiry in Central timezone.
        """
        expiry = dt.datetime.strptime(str(date), "%Y%m%d")
        if am_settlement == 1:
            expiry = expiry.replace(hour=8, minute=30)
        elif am_settlement == 0:
            expiry = expiry.replace(hour=15, minute=0)
        else:
            raise ValueError(f"Unsupported am_settlement: {am_settlement}")

        return expiry
