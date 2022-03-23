"""
Module containing filters to discard raw IV markets that we do not want to fit.
"""

import abc
import datetime as dt
import logging
import math
import numpy as np

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
            expiry: self._filter_expiry(curve, pricing)
            for (expiry, curve) in raw_iv_surface.curves.items()
        }
        return RawIVSurface(raw_iv_surface.datetime, filtered_curves)

    def _filter_expiry(
        self, raw_iv_curve: RawIVCurve, pricing: Dict[Option, Pricing]
    ) -> RawIVCurve:
        """
        Filters a single raw IV curve.
        :param raw_iv_surface: RawIVCurve.
        :param pricing: Dict of Pricings.
        :return: Filtered RawIVCurve.
        """

        retained_points = {
            option: point
            for (option, point) in raw_iv_curve.points.items()
            if not self._discard_point(point, pricing)
        }

        self._log_if_necessary(
            raw_iv_curve.expiry,
            len(raw_iv_curve.points) - len(retained_points),
            len(raw_iv_curve.points),
        )

        return RawIVCurve(raw_iv_curve.expiry, raw_iv_curve.status, retained_points)

    @abc.abstractmethod
    def _discard_point(
        self, raw_iv_point: RawIVPoint, pricing: Dict[Option, Pricing]
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
        self, raw_iv_point: RawIVPoint, pricing: Dict[Option, Pricing]
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
        self, raw_iv_point: RawIVPoint, pricing: Dict[Option, Pricing]
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
        self, raw_iv_curve: RawIVCurve, pricing: Dict[Option, Pricing]
    ) -> RawIVCurve:
        """
        Marks a RawIVCurve as FAILed if it does not have enough valid strikes.

        If the RawIVCurve is already FAILed, that failure status message is propagated
        rather than overwritten.

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
        self, raw_iv_point: RawIVPoint, pricing: Dict[Option, Pricing]
    ) -> bool:
        raise NotImplementedError
