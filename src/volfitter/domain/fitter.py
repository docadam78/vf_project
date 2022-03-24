"""
Module containing volatility surface fitters.

This module contains both the abstract fitter interface and its concrete
implementations.
"""

import abc
import datetime as dt
import numpy as np

from scipy import linalg, optimize
from typing import Dict, Tuple, Union

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
    SVIParameters,
    RawIVPoint,
    Status,
    fail,
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


class AbstractSVICalibrator(abc.ABC):
    """
    Abstract base class for SVI implied variance model calibrators.
    """

    @abc.abstractmethod
    def calibrate(
        self,
        expiry: dt.datetime,
        moneyness: np.ndarray,
        variance: np.ndarray,
        time_to_expiry: float,
    ) -> Tuple[SVIParameters, Status]:
        """
        Calibrates the SVI implied variance model to the given time slice.

        :param expiry: The expiry.
        :param moneyness: The log-moneynesses of the expiry.
        :param variance: The implied variances to be fitted.
        :param time_to_expiry: The time to expiry.
        :return: The calibrated model parameters and the calibration status.
        """
        raise NotImplementedError


class UnconstrainedQuasiExplicitSVICalibrator(AbstractSVICalibrator):
    """
    Implements the quasi-explicit SVI calibration of Zeliade 2012, but without constraints.

    This class implements the quasi-explicit calibration of SVI described in Zeliade
    2012, but we do not include the constraints they include in their "reduced problem"
    in their Section 3.1. This is because including the constraints materially worsens
    the fit quality. The most important constraint is an arbitrage constraint to
    guarantee the absence of vertical spread arbitrage. The other two constraints are merely
    to help with parameter stability from one run to the next, but I find that even
    these result in degraded fit quality.

    The constrained minimization problem is a convex optimization problem with
    quadratic cost function. Without constraints, it becomes entirely linear.
    """

    def __init__(self):
        self.previous_calibrated_parameters = {}

    def calibrate(
        self,
        expiry: dt.datetime,
        moneyness: np.ndarray,
        variance: np.ndarray,
        time_to_expiry: float,
    ) -> Tuple[SVIParameters, Status]:
        """
        Performs an unconstrained version of Zeliade 2012's quasi-explicit SVI calibration.

        The calibration consists of an outer and an inner stage. The inner stage fixes
        two of the five model parameters and then solves a linear system of equations
        to find the optimal three remaining parameters as a function of the given two.
        The outer stage then optimizes those two parameters. We use the Nelder-Mead
        simplex algorithm for the outer optimization, which is a good default choice
        for general problems and is also what Zeliade 2012 use.

        See Section 3 of Zeliade 2012 for more details.

        Zeliade 2012 is also reproduced, with slightly more detail, as Section 5 of
        Stefano De Marco's PhD thesis (De Marco 2010). Section 5.3.2 of De Marco 2010
        provides the gradient of the inner cost function which we implement here, and
        which is not included in Zeliade 2012 (although it is easy to derive by hand).

        We choose to initialize the outer Nelder-Mead optimization at the previously
        calibrated parameters for this expiry if they exist. This is not expected to
        make much difference, as the calibration methodology is fairly insensitive to
        the initial guess.

        The smoothness parameter is floored at 0.005 as suggested in Zeliade 2012
        Section 2.3, though this is mostly for parameter stability and is not expected
        to materially affect the fit quality.

        If the outer minimization problem fails to terminate successfully, the failure
        is propagated to the caller of calibrate.

        :param expiry: The expiry.
        :param moneyness: The log-moneynesses of the expiry.
        :param variance: The implied variances to be fitted.
        :param time_to_expiry: The time to expiry.
        :return: The calibrated model parameters and the calibration status.
        """

        def outer_cost_function(candidate_params: np.ndarray) -> float:
            level, angle, tilt = self._solve_reduced_problem(
                moneyness,
                variance,
                time_to_expiry,
                candidate_params[0],
                candidate_params[1],
            )

            svi_variance = _svi_implied_variance(
                moneyness, level, angle, candidate_params[0], tilt, candidate_params[1]
            )

            # noinspection PyTypeChecker
            return np.sum((svi_variance - variance) ** 2)

        if expiry in self.previous_calibrated_parameters:
            initial_smoothness = self.previous_calibrated_parameters[expiry].smoothness
            initial_center = self.previous_calibrated_parameters[expiry].center
        else:
            initial_smoothness = 0.005
            initial_center = 0

        initial_guess = np.array([initial_smoothness, initial_center])
        bounds = [(0.005, None), (None, None)]

        optimize_result = optimize.minimize(
            outer_cost_function, initial_guess, bounds=bounds, method="Nelder-Mead"
        )

        status = ok() if optimize_result.success else fail(optimize_result.message)

        smoothness, center = optimize_result.x[0], optimize_result.x[1]
        level, angle, tilt = self._solve_reduced_problem(
            moneyness, variance, time_to_expiry, smoothness, center
        )
        calibrated_parameters = SVIParameters(level, angle, smoothness, tilt, center)

        if status.tag == Tag.OK:
            self.previous_calibrated_parameters[expiry] = calibrated_parameters

        return calibrated_parameters, status

    def _solve_reduced_problem(
        self,
        moneyness: np.ndarray,
        variance: np.ndarray,
        time_to_expiry: float,
        smoothness: float,
        center: float,
    ) -> Tuple[float, float, float]:
        """
        Solves an unconstrained version of the inner "reduced problem" described in
        Section 3.1 of Zeliade 2012. We omit the constraints described there, making
        the problem entirely linear.

        See Section 5.3.2 of De Marco 2010 for the gradient of the cost function as it
        is implemented here. My variable names for the entries of the gradient (Y_1,
        Y_2, Y_3, Y_4, vY_2, vY, and v) correspond to the De Marco 2010 notation, for
        lack of more descriptive names for these quantities.

        :param moneyness: The log-moneynesses of the expiry.
        :param variance: The implied variances to be fitted.
        :param time_to_expiry: The time to expiry.
        :param smoothness: A given smoothness parameter.
        :param center: A given center parameter.
        :return: The optimal level, angle, and tilt, given the supplied smoothness and
            center.
        """

        num_points = len(moneyness)
        transformed_moneyness = (moneyness - center) / smoothness
        total_variance = variance * time_to_expiry

        Y_1 = np.sum(transformed_moneyness)
        Y_2 = np.sum(transformed_moneyness**2)
        Y_3 = np.sum(np.sqrt(transformed_moneyness**2 + 1))
        Y_4 = np.sum(transformed_moneyness * np.sqrt(transformed_moneyness**2 + 1))

        vY_2 = np.sum(total_variance * np.sqrt(transformed_moneyness**2 + 1))
        vY = np.sum(total_variance * transformed_moneyness)
        v = np.sum(total_variance)

        A = np.array(
            [[num_points + Y_2, Y_4, Y_3], [Y_4, Y_2, Y_1], [Y_3, Y_1, num_points]]
        )
        b = np.array([vY_2, vY, v])

        x = linalg.solve(A, b)

        # These are c, d, and \tilde{a}, respectively, in the notation of Zeliade 2012
        transformed_angle, transformed_tilt, transformed_level = x[0], x[1], x[2]

        level = transformed_level / time_to_expiry
        angle = transformed_angle / (smoothness * time_to_expiry)
        tilt = transformed_tilt / transformed_angle

        return level, angle, tilt


class SVISurfaceFitter(AbstractPerExpirySurfaceFitter):
    """
    Fits the Stochastic Volatility Inspired (SVI) implied variance model to each expiry independently.

    In particular, no attempt is made to enforce absence of calendar arbitrage.
    Vertical spread arbitrage may or may not be removed, depending on the implementation
    of AbstractSVICalibrator that is supplied.

    See Gatheral 2004 for details of the SVI model.
    """

    def __init__(self, calibrator: AbstractSVICalibrator):
        self.calibrator = calibrator

    def _fit_curve_model(
        self, raw_iv_curve: RawIVCurve, pricings: Dict[Option, Pricing]
    ) -> FinalIVCurve:
        """
        Fits the SVI model to the mid-market implied vols of a single expiry.

        If the input raw vol curve is marked as WARN or FAIL, that status is propagated
        and the SVI curve is not fit.

        The status of the final curve is set to the status of the calibration.

        :param raw_iv_curve: The raw vol curve.
        :param pricing: Dict of option pricing.
        :return: The final, fitted vol curve.
        """

        if raw_iv_curve.status.tag != Tag.OK:
            return FinalIVCurve(raw_iv_curve.expiry, raw_iv_curve.status, {})

        moneyness = np.zeros(len(raw_iv_curve.points))
        raw_variance = np.zeros(len(raw_iv_curve.points))
        for i, point in enumerate(raw_iv_curve.points.values()):
            moneyness[i] = pricings[point.option].moneyness
            raw_variance[i] = self._calc_midmarket_implied_variance(point)

        # All options in the expiry are assumed to have the same time to expiry, so we
        # take an arbitrary one.
        time_to_expiry = pricings[
            next(iter(raw_iv_curve.points.values())).option
        ].time_to_expiry

        svi_parameters, status = self.calibrator.calibrate(
            raw_iv_curve.expiry, moneyness, raw_variance, time_to_expiry
        )

        # Return the modeled final vol for all listed strikes in the expiry, not just
        # the subset of strikes we calibrated to.
        final_iv_points = {
            pricing.option.strike: FinalIVPoint(
                raw_iv_curve.expiry,
                pricing.option.strike,
                np.sqrt(
                    _svi_implied_variance(
                        pricing.moneyness,
                        svi_parameters.level,
                        svi_parameters.angle,
                        svi_parameters.smoothness,
                        svi_parameters.tilt,
                        svi_parameters.center,
                    )
                ),
            )
            for pricing in pricings.values()
            if pricing.option.expiry == raw_iv_curve.expiry
        }

        return FinalIVCurve(raw_iv_curve.expiry, status, final_iv_points)

    def _calc_midmarket_implied_variance(self, raw_iv_point: RawIVPoint) -> float:
        return _midpoint(raw_iv_point.bid_vol, raw_iv_point.ask_vol) ** 2


def _svi_implied_variance(
    moneyness: Union[float, np.ndarray],
    level: float,
    angle: float,
    smoothness: float,
    tilt: float,
    center: float,
) -> Union[float, np.ndarray]:
    distance = moneyness - center
    return level + angle * (tilt * distance + np.sqrt(distance**2 + smoothness**2))


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
