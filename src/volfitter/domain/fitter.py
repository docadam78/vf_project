"""
Module containing volatility surface fitters.

This module contains both the abstract fitter interface and its concrete
implementations.
"""

import abc
from typing import Dict

import numpy as np

from volfitter.domain.datamodel import (
    FinalIVSurface,
    RawIVSurface,
    RawIVCurve,
    FinalIVCurve,
    FinalIVPoint,
    Tag,
    ok,
    Pricing,
    Option,
)


class AbstractSurfaceFitter(abc.ABC):
    """
    Abstract base class for vol surface fitters.
    """

    @abc.abstractmethod
    def fit_surface_model(
        self, raw_iv_surface: RawIVSurface, pricing: Dict[Option, Pricing]
    ) -> FinalIVSurface:
        """
        Fits a vol surface model to a raw vol surface.

        :param raw_iv_surface: The raw vol surface.
        :param pricing: Dict of option pricing.
        :return: The final, fitted vol surface.
        """
        raise NotImplementedError


class AbstractPerExpirySurfaceFitter(AbstractSurfaceFitter):
    """
    Abstract base class for vol surface fitters which fit each expiry independently.
    """

    def fit_surface_model(
        self, raw_iv_surface: RawIVSurface, pricing: Dict[Option, Pricing]
    ) -> FinalIVSurface:
        """
        Fits a vol surface model to a raw vol surface, fitting each expiry
        independently.

        :param raw_iv_surface: The raw vol surface.
        :param pricing: Dict of option pricing.
        :return: The final, fitted vol surface.
        """
        final_iv_curves = {
            expiry: self._fit_curve_model(curve, pricing)
            for (expiry, curve) in raw_iv_surface.curves.items()
        }

        return FinalIVSurface(raw_iv_surface.datetime, final_iv_curves)

    @abc.abstractmethod
    def _fit_curve_model(
        self, raw_iv_curve: RawIVCurve, pricing: Dict[Option, Pricing]
    ) -> FinalIVCurve:
        """
        Fits a vol curve model to a raw vol curve.

        :param raw_iv_curve: The raw vol curve.
        :param pricing: Dict of option pricing.
        :return: The final, fitted vol curve.
        """
        raise NotImplementedError


class MidMarketSurfaceFitter(AbstractPerExpirySurfaceFitter):
    """
    Mid-market placeholder vol fitter which does as little work as possible.

    This vol "fitter" is simply a toy implementation to demonstrate how different
    fitters could be plugged in.
    """

    def _fit_curve_model(
        self, raw_iv_curve: RawIVCurve, pricing: Dict[Option, Pricing]
    ) -> FinalIVCurve:
        """
        Transforms a raw curve to a final curve doing as little work as possible.

        Returns a final vol surface which is simply the midpoint
        of the raw bid and ask vols at each strike. At each strike, the combined
        tightest market between the call and put is used (so in particular, the bid
        and ask do not have to come from the same option).

        If the status of the input curve is not OK, the curve is not fit: An empty
        curve with the propagated non-OK status is returned.

        :param raw_iv_curve: The raw vol curve.
        :param pricing: Dict of option pricing.
        :return: The final, fitted vol curve.
        """

        if raw_iv_curve.status.tag != Tag.OK:
            return FinalIVCurve(raw_iv_curve.expiry, raw_iv_curve.status, {})

        best_bids_by_strike = {}
        best_asks_by_strike = {}

        for (option, raw_iv_point) in raw_iv_curve.points.items():
            strike = option.strike
            if raw_iv_point.bid_vol > best_bids_by_strike.get(strike, -np.inf):
                best_bids_by_strike[strike] = raw_iv_point.bid_vol

            if raw_iv_point.ask_vol < best_asks_by_strike.get(strike, np.inf):
                best_asks_by_strike[strike] = raw_iv_point.ask_vol

        final_iv_points = {
            strike: FinalIVPoint(
                raw_iv_curve.expiry,
                strike,
                _midpoint(best_bids_by_strike[strike], best_asks_by_strike[strike]),
            )
            for strike in best_bids_by_strike.keys()
        }

        return FinalIVCurve(raw_iv_curve.expiry, ok(), final_iv_points)


def _midpoint(bid: float, ask: float) -> float:
    return 0.5 * (bid + ask)
