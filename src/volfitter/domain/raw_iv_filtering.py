"""
Module containing filters to discard raw IV markets that we do not want to fit.
"""

import abc
from typing import List, Dict

from volfitter.domain.datamodel import (
    RawIVSurface,
    RawIVCurve,
    Pricing,
    Option,
    RawIVPoint,
    OptionKind,
)


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

        points = {
            option: point
            for (option, point) in raw_iv_curve.points.items()
            if not self._discard_point(point, pricing)
        }
        return RawIVCurve(raw_iv_curve.expiry, points)

    @abc.abstractmethod
    def _discard_point(
        self, raw_iv_point: RawIVPoint, pricing: Dict[Option, Pricing]
    ) -> bool:
        raise NotImplementedError


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
