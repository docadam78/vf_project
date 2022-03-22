"""
Module containing ports and adaptors for pricing suppliers.

Contains both the abstract interface and concrete implementation.
"""

import abc
import datetime as dt
import math

from typing import Dict, Collection

from volfitter.adapters.option_metrics_helpers import create_option
from volfitter.adapters.sample_data_loader import AbstractDataFrameSupplier
from volfitter.domain.datamodel import Option, Pricing, ForwardCurve


class AbstractPricingSupplier(abc.ABC):
    """
    Abstract base class for pricing suppliers.
    """

    @abc.abstractmethod
    def get_pricing(
        self,
        datetime: dt.datetime,
        forward_curve: ForwardCurve,
        options: Collection[Option],
    ) -> Dict[Option, Pricing]:
        """
        Returns a dict of Pricing for each Option.

        :param datetime: The datetime for which to return pricing.
        :param forward_curve: The forward curve to use when constructing the pricing.
        :param options: The options for which to return pricing.
        :return: Dict[Option, Pricing].
        """
        raise NotImplementedError


class OptionMetricsPricingSupplier(AbstractPricingSupplier):
    """
    Creates Pricing objects from OptionMetrics data.
    """

    def __init__(self, option_dataframe_supplier: AbstractDataFrameSupplier):
        self.option_dataframe_supplier = option_dataframe_supplier

    def get_pricing(
        self,
        datetime: dt.datetime,
        forward_curve: ForwardCurve,
        options: Collection[Option],
    ) -> Dict[Option, Pricing]:
        """
        Creates Pricing objects from OptionMetrics data.

        Combines the data read from disc with the supplied forward curve to construct
        pricing.

        :param datetime: The datetime for which to return pricing.
        :param forward_curve: The forward curve to use when constructing the pricing.
        :param options: The options for which to return pricing.
        :return: Dict[Option, Pricing].
        """

        df = self.option_dataframe_supplier.get_dataframe(datetime)

        rows = zip(
            df["symbol"].values,
            df["exdate"].values,
            df["am_settlement"].values,
            df["strike_price"].values,
            df["cp_flag"].values,
            df["exercise_style"].values,
            df["contract_size"].values,
            df["delta"].values,
            df["gamma"].values,
            df["vega"].values,
            df["theta"].values,
        )

        all_pricings = {}
        for (*option_specs, delta, gamma, vega, theta) in rows:
            option = create_option(*option_specs)
            forward = forward_curve.forward_prices[option.expiry]
            pricing = self._create_pricing(
                datetime, option, forward, delta, gamma, vega, theta
            )

            all_pricings[option] = pricing

        requested_pricings = {}
        for option in options:
            if option not in all_pricings:
                raise ValueError(f"Missing pricing for {option}!")

            requested_pricings[option] = all_pricings[option]

        return requested_pricings

    def _create_pricing(
        self,
        current_time: dt.datetime,
        option: Option,
        forward: float,
        delta: float,
        gamma: float,
        vega: float,
        theta: float,
    ) -> Pricing:
        moneyness = _calculate_moneyness(option.strike, forward)
        time_to_expiry = _calculate_time_to_expiry(current_time, option.expiry)

        return Pricing(option, moneyness, delta, gamma, vega, theta, time_to_expiry)


def _calculate_moneyness(strike: float, forward: float) -> float:
    """
    Returns the log-moneyness.

    There are many different definitions of moneyness in the options world, mainly
    differentiated by what they have in their denominator. The log-moneyness we use
    here is perhaps the simplest, having only 1 in its denominator. While other
    definitions of moneyness may be more suitable in other applications, this is the
    definition used in the literature surrounding the model we implement in this
    project.

    :param strike: The option strike.
    :param forward: The forward price at the option expiry.
    :return: The log-moneyness.
    """

    return math.log(strike / forward)


def _calculate_time_to_expiry(current_time: dt.datetime, expiry: dt.datetime) -> float:
    """
    Returns the time to expiry.

    The time to expiry is calculated using an ACT/365 day count convention. This means
    that, in particular, leap days are included in the numerator but not in the
    denominator.

    This quantity represents the "wall clock time" to expiry, and does not make
    any adjustment for the fact that "business time" may elapse slower on weekends or
    outside of market hours.

    :param current_time: The current time.
    :param expiry: The time of the option expiry.
    :return: The time to expiry as a fraction of a 365-day year.
    """

    return (expiry - current_time) / dt.timedelta(days=365)
