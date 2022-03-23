"""
Module containing filters to discard raw IV markets that we do not want to fit.
"""

import abc
import datetime as dt
import logging
import math
import numpy as np
import pandas_market_calendars as mcal

from typing import List, Dict

from volfitter.config import VolfitterConfig
from volfitter.domain.datamodel import (
    RawIVSurface,
    RawIVCurve,
    Pricing,
    Option,
    RawIVPoint,
    OptionKind,
    Tag,
    fail,
)

_LOGGER = logging.getLogger(__name__)


class AbstractRawIVFilter(abc.ABC):
    """
    Abstract base class for raw IV filters.
    """

    @abc.abstractmethod
    def filter_raw_ivs(
        self, raw_iv_surface: RawIVSurface, pricing: Dict[Option, Pricing]
    ) -> RawIVSurface:
        """
        Filters the raw IV surface.
        :param raw_iv_surface: RawIVSurface.
        :param pricing: Dict of Pricings.
        :return: Filtered RawIVSurface.
        """
        raise NotImplementedError


class AbstractPerExpiryRawIVFilter(AbstractRawIVFilter):
    """
    Abstract base class for raw IV filters that operate per expiry.
    """

    def filter_raw_ivs(
        self, raw_iv_surface: RawIVSurface, pricing: Dict[Option, Pricing]
    ) -> RawIVSurface:
        """
        Filters the raw IV surface, fitering each expiry independently.
        :param raw_iv_surface: RawIVSurface.
        :param pricing: Dict of Pricings.
        :return: Filtered RawIVSurface.
        """

        filtered_curves = {
            expiry: self._filter_expiry(raw_iv_surface.datetime, curve, pricing)
            for (expiry, curve) in raw_iv_surface.curves.items()
        }
        return RawIVSurface(raw_iv_surface.datetime, filtered_curves)

    def _filter_expiry(
        self,
        current_time: dt.datetime,
        raw_iv_curve: RawIVCurve,
        pricing: Dict[Option, Pricing],
    ) -> RawIVCurve:
        """
        Filters a single raw IV curve.
        :param current_time: The current time.
        :param raw_iv_surface: RawIVCurve.
        :param pricing: Dict of Pricings.
        :return: Filtered RawIVCurve.
        """

        retained_points = {
            option: point
            for (option, point) in raw_iv_curve.points.items()
            if not self._discard_point(current_time, point, pricing)
        }

        self._log_if_necessary(
            raw_iv_curve.expiry,
            len(raw_iv_curve.points) - len(retained_points),
            len(raw_iv_curve.points),
        )

        return RawIVCurve(raw_iv_curve.expiry, raw_iv_curve.status, retained_points)

    @abc.abstractmethod
    def _discard_point(
        self,
        current_time: dt.datetime,
        raw_iv_point: RawIVPoint,
        pricing: Dict[Option, Pricing],
    ) -> bool:
        raise NotImplementedError

    def _log_if_necessary(
        self, expiry: dt.datetime, num_discarded_points: int, num_original_points: int
    ) -> None:
        pass


class CompositeRawIVFilter(AbstractRawIVFilter):
    """
    Successively applies each filter in a list.
    """

    def __init__(self, filters: List[AbstractRawIVFilter]):
        self.filters = filters

    def filter_raw_ivs(
        self, raw_iv_surface: RawIVSurface, pricing: Dict[Option, Pricing]
    ) -> RawIVSurface:
        """
        Filters the raw IV surface by successively applying each filter in a list.
        :param raw_iv_surface: RawIVSurface.
        :param pricing: Dict of Pricings.
        :return: Filtered RawIVSurface.
        """

        filtered_surface = raw_iv_surface
        for filter in self.filters:
            filtered_surface = filter.filter_raw_ivs(filtered_surface, pricing)

        return filtered_surface


class InTheMoneyFilter(AbstractPerExpiryRawIVFilter):
    """
    Discards in-the-money options.
    """

    def _discard_point(
        self,
        current_time: dt.datetime,
        raw_iv_point: RawIVPoint,
        pricing: Dict[Option, Pricing],
    ) -> bool:
        kind = raw_iv_point.option.kind
        moneyness = pricing[raw_iv_point.option].moneyness

        return (kind == OptionKind.CALL and moneyness < 0) or (
            kind == OptionKind.PUT and moneyness > 0
        )


class NonTwoSidedMarketFilter(AbstractPerExpiryRawIVFilter):
    """
    Discards empty and one-sided markets, i.e., markets whose bid vol or ask vol is NaN.
    """

    def _discard_point(
        self,
        current_time: dt.datetime,
        raw_iv_point: RawIVPoint,
        pricing: Dict[Option, Pricing],
    ) -> bool:
        return np.isnan(raw_iv_point.bid_vol) or np.isnan(raw_iv_point.ask_vol)

    def _log_if_necessary(
        self, expiry: dt.datetime, num_discarded_points: int, num_original_points: int
    ) -> None:
        if num_discarded_points > 0:
            _LOGGER.info(
                f"Discarding {num_discarded_points} of {num_original_points} strikes "
                f"in expiry {expiry} because they were empty or one-sided."
            )


class StaleLastTradeDateFilter(AbstractPerExpiryRawIVFilter):
    """
    Discards markets whose last trade date is too old.

    The max allowable last trade age is specified in configuration. We count business
    days using the NYSE holiday calendar.
    """

    def __init__(self, raw_iv_filtering_config: VolfitterConfig.RawIVFilteringConfig):
        self.raw_iv_filtering_config = raw_iv_filtering_config
        self.holidays = mcal.get_calendar("NYSE").holidays().holidays

    def _discard_point(
        self,
        current_time: dt.datetime,
        raw_iv_point: RawIVPoint,
        pricing: Dict[Option, Pricing],
    ) -> bool:
        last_trade_age = np.busday_count(
            raw_iv_point.last_trade_date, current_time.date(), holidays=self.holidays
        )
        return last_trade_age > self.raw_iv_filtering_config.max_last_trade_age_days

    def _log_if_necessary(
        self, expiry: dt.datetime, num_discarded_points: int, num_original_points: int
    ) -> None:
        if num_discarded_points > 0:
            _LOGGER.info(
                f"Discarding {num_discarded_points} of {num_original_points} strikes "
                f"in expiry {expiry} because their last trade date was older than "
                f"{self.raw_iv_filtering_config.max_last_trade_age_days} days."
            )


class WideMarketFilter(AbstractPerExpiryRawIVFilter):
    """
    Discards markets which are wide outliers relative to their expiry's typical market width.
    """

    def __init__(self, raw_iv_filtering_config: VolfitterConfig.RawIVFilteringConfig):
        self.raw_iv_filtering_config = raw_iv_filtering_config

    def _filter_expiry(
        self,
        current_time: dt.datetime,
        raw_iv_curve: RawIVCurve,
        pricing: Dict[Option, Pricing],
    ) -> RawIVCurve:
        """
        Discards wide market outliers.

        The outlier detection works by first calculating the median and median absolute
        deviation (MAD) of the market widths in the expiry. The median and MAD are
        measures of central tendency and dispersion, respectively, that are robust to
        outliers.

        Then, markets which are wider than a configurable amount of MADs beyond the
        median width are discarded.

        :param current_time: The current time.
        :param raw_iv_surface: RawIVCurve.
        :param pricing: Dict of Pricings.
        :return: Filtered RawIVCurve.
        """

        market_widths = np.array(
            [self._calc_market_width(point) for point in raw_iv_curve.points.values()]
        )

        # Suppress PyCharm type checker warnings: It thinks that the numpy calls are
        # returning ndarrays, which is true in general, but because we are passing them
        # 1-dimensional input arrays the return type in our case is actually a float.

        # noinspection PyTypeChecker
        median_width: float = np.median(market_widths)
        # noinspection PyTypeChecker
        median_absolute_deviation: float = np.median(
            np.abs(market_widths - median_width)
        )

        retained_points = {
            option: point
            for (option, point) in raw_iv_curve.points.items()
            if not self._too_wide(point, median_width, median_absolute_deviation)
        }

        self._log_if_necessary(
            raw_iv_curve.expiry,
            len(raw_iv_curve.points) - len(retained_points),
            len(raw_iv_curve.points),
        )

        return RawIVCurve(raw_iv_curve.expiry, raw_iv_curve.status, retained_points)

    def _too_wide(
        self, raw_iv_point: RawIVPoint, width_median: float, width_mad: float
    ) -> bool:
        return (
            self._calc_market_width(raw_iv_point) - width_median
            > self.raw_iv_filtering_config.wide_market_outlier_mad_threshold * width_mad
        )

    def _calc_market_width(self, raw_iv_point: RawIVPoint) -> float:
        return raw_iv_point.ask_vol - raw_iv_point.bid_vol

    def _log_if_necessary(
        self, expiry: dt.datetime, num_discarded_points: int, num_original_points: int
    ) -> None:
        if num_discarded_points > 0:
            _LOGGER.info(
                f"Discarding {num_discarded_points} of {num_original_points} strikes "
                f"in expiry {expiry} because they were too wide."
            )

    def _discard_point(
        self,
        current_time: dt.datetime,
        raw_iv_point: RawIVPoint,
        pricing: Dict[Option, Pricing],
    ) -> bool:
        raise NotImplementedError


class InsufficientValidStrikesFilter(AbstractPerExpiryRawIVFilter):
    """
    Marks a RawIVCurve as FAILed if it does not have enough valid strikes.

    "Valid" is defined as "not having been filtered out by any earlier RawIVFilters."

    "Enough" is defined as "at least the larger of the configured
    min_valid_strikes_fraction multiplied by the number of listed strikes, and three."
    """

    _MIN_STRIKES = 3

    def __init__(self, raw_iv_filtering_config: VolfitterConfig.RawIVFilteringConfig):
        self.raw_iv_filtering_config = raw_iv_filtering_config

    def _filter_expiry(
        self,
        current_time: dt.datetime,
        raw_iv_curve: RawIVCurve,
        pricing: Dict[Option, Pricing],
    ) -> RawIVCurve:
        """
        Marks a RawIVCurve as FAILed if it does not have enough valid strikes.

        If the RawIVCurve is already FAILed, that failure status message is propagated
        rather than overwritten.

        :param current_time: The current time.
        :param raw_iv_surface: RawIVCurve.
        :param pricing: Dict of Pricings.
        :return: RawIVCurve, potentially with its status set to FAIL.
        """

        if raw_iv_curve.status.tag == Tag.FAIL:
            return raw_iv_curve

        num_strikes_in_expiry = len(
            set(
                [
                    option.strike
                    for option in pricing.keys()
                    if option.expiry == raw_iv_curve.expiry
                ]
            )
        )

        min_valid_strikes = max(
            self.raw_iv_filtering_config.min_valid_strikes_fraction
            * num_strikes_in_expiry,
            InsufficientValidStrikesFilter._MIN_STRIKES,
        )

        if len(raw_iv_curve.points) < min_valid_strikes:
            _LOGGER.warning(
                f"Expiry {raw_iv_curve.expiry} has too few valid strikes and will not "
                f"be fit. Required {int(math.ceil(min_valid_strikes))} valid strikes."
            )
            return RawIVCurve(
                raw_iv_curve.expiry,
                fail("Insufficient valid strikes."),
                raw_iv_curve.points,
            )
        else:
            return raw_iv_curve

    def _discard_point(
        self,
        current_time: dt.datetime,
        raw_iv_point: RawIVPoint,
        pricing: Dict[Option, Pricing],
    ) -> bool:
        raise NotImplementedError
