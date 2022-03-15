"""
Module containing volatility surface fitters.

This module contains both the abstract fitter interface and its concrete
implementations.
"""

import abc
import numpy as np

from src.volfitter.domain.datamodel import (
    FinalIVSurface,
    RawIVSurface,
    RawIVCurve,
    FinalIVCurve,
    FinalIVPoint,
)


class AbstractSurfaceFitter(abc.ABC):
    """
    Abstract base class for vol surface fitters.
    """

    @abc.abstractmethod
    def fit_surface_model(self, raw_iv_surface: RawIVSurface) -> FinalIVSurface:
        """
        Fits a vol surface model to a raw vol surface.

        :param raw_iv_surface: The raw vol surface.
        :return: The final, fitted vol surface.
        """
        raise NotImplementedError


class AbstractPerExpirySurfaceFitter(AbstractSurfaceFitter):
    """
    Abstract base class for vol surface fitters which fit each expiry independently.
    """

    def fit_surface_model(self, raw_iv_surface: RawIVSurface) -> FinalIVSurface:
        """
        Fits a vol surface model to a raw vol surface, fitting each expiry independently.

        :param raw_iv_surface: The raw vol surface.
        :return: The final, fitted vol surface.
        """
        final_iv_curves = {
            raw_iv_curve.expiry: self._fit_curve_model(raw_iv_curve)
            for raw_iv_curve in raw_iv_surface.curves
        }

        return FinalIVSurface(final_iv_curves)

    @abc.abstractmethod
    def _fit_curve_model(self, raw_iv_curve: RawIVCurve) -> FinalIVCurve:
        """
        Fits a vol curve model to a raw vol curve.

        :param raw_iv_curve: The raw vol curve.
        :return: The final, fitted vol curve.
        """
        raise NotImplementedError


class PassThroughSurfaceFitter(AbstractPerExpirySurfaceFitter):
    """
    Pass-through placeholder vol fitter which does as little work as possible.
    """

    def _fit_curve_model(self, raw_iv_curve: RawIVCurve) -> FinalIVCurve:
        """
        Transforms a raw curve to a final curve doing as little work as possible.

        Returns a final vol surface which is simply the midpoint
        of the raw bid and ask vols at each strike. At each strike, the combined
        tightest market between the call and put is used (so in particular, the bid
        and ask do not have to come from the same option).

        :param raw_iv_curve: The raw vol curve.
        :return: The final, fitted vol curve.
        """

        best_bids_by_strike = {}
        best_asks_by_strike = {}

        for raw_iv_point in raw_iv_curve.points:
            strike = raw_iv_point.option.strike
            if raw_iv_point.bid_vol > best_bids_by_strike.get(strike, -np.inf):
                best_bids_by_strike[strike] = raw_iv_point.bid_vol

            if raw_iv_point.ask_vol < best_asks_by_strike.get(strike, np.inf):
                best_asks_by_strike[strike] = raw_iv_point.ask_vol

        final_iv_points = {
            strike: FinalIVPoint(
                raw_iv_curve.expiry,
                strike,
                midpoint(best_bids_by_strike[strike], best_asks_by_strike[strike]),
            )
            for strike in best_bids_by_strike.keys()
        }

        return FinalIVCurve(raw_iv_curve.expiry, final_iv_points)


def midpoint(bid: float, ask: float) -> float:
    return 0.5 * (bid + ask)
