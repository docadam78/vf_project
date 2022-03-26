"""
Module containing safety checks to validate the final fitted IV surface.
"""

import abc
import logging
import numpy as np

from typing import Dict, List

from volfitter.config import VolfitterConfig
from volfitter.domain.datamodel import (
    FinalIVSurface,
    RawIVSurface,
    Pricing,
    Option,
    FinalIVCurve,
    RawIVCurve,
    Tag,
    RawIVPoint,
    FinalIVPoint,
    fail,
    warn,
)

_LOGGER = logging.getLogger(__name__)


class AbstractFinalIVValidator(abc.ABC):
    """
    Abstract base class for final IV validators.
    """

    @abc.abstractmethod
    def validate_final_ivs(
        self,
        final_iv_surface: FinalIVSurface,
        unfiltered_raw_iv_surface: RawIVSurface,
        pricing: Dict[Option, Pricing],
    ) -> FinalIVSurface:
        """
        Validates the final IV surface.

        "Validation" means setting the status of each curve to WARN or FAIL if any
        safety checks are validated.

        :param final_iv_surface: FinalIVSurface.
        :param unfiltered_raw_iv_surface: Unfiltered RawIVSurface. We use the unfiltered
            surface so that the validation can use all raw markets, even those that were
            not used in the calibration.
        :param pricing: Dict of Pricings.
        :return: FinalIVSurface, possibly with modified curve statuses.
        """
        raise NotImplementedError


class AbstractPerExpiryFinalIVValidator(AbstractFinalIVValidator):
    """
    Abstract base class for final IV validators that operate per expiry.
    """

    def validate_final_ivs(
        self,
        final_iv_surface: FinalIVSurface,
        unfiltered_raw_iv_surface: RawIVSurface,
        pricing: Dict[Option, Pricing],
    ) -> FinalIVSurface:
        """
        Validates the final IV surface, validating each expiry independently.

        :param final_iv_surface: FinalIVSurface.
        :param unfiltered_raw_iv_surface: Unfiltered RawIVSurface.
        :param pricing: Dict of Pricings.
        :return: FinalIVSurface, possibly with modified curve statuses.
        """

        validated_curves = {
            expiry: self._validate_expiry(
                curve, unfiltered_raw_iv_surface.curves[expiry], pricing
            )
            for (expiry, curve) in final_iv_surface.curves.items()
        }
        return FinalIVSurface(final_iv_surface.datetime, validated_curves)

    @abc.abstractmethod
    def _validate_expiry(
        self,
        final_iv_curve: FinalIVCurve,
        unfiltered_raw_iv_curve: RawIVCurve,
        pricing: Dict[Option, Pricing],
    ) -> FinalIVCurve:
        """
        Validates a single final IV curve.

        :param final_iv_curve: FinalIVCurve.
        :param unfiltered_raw_iv_curve: Unfiltered RawIVCurve.
        :param pricing: Dict of Pricings.
        :return: FinalIVCurve, possibly with modified status.
        """
        raise NotImplementedError


class CompositeFinalIVValidator(AbstractFinalIVValidator):
    """
    Successively applies each validator in a list.
    """

    def __init__(self, validators: List[AbstractFinalIVValidator]):
        self.validators = validators

    def validate_final_ivs(
        self,
        final_iv_surface: FinalIVSurface,
        unfiltered_raw_iv_surface: RawIVSurface,
        pricing: Dict[Option, Pricing],
    ) -> FinalIVSurface:
        """
        Validates the final IV surface by successively applying each validator in a list.

        :param final_iv_surface: FinalIVSurface.
        :param unfiltered_raw_iv_surface: Unfiltered RawIVSurface.
        :param pricing: Dict of Pricings.
        :return: FinalIVSurface, possibly with modified curve statuses.
        """

        validated_surface = final_iv_surface
        for validator in self.validators:
            validated_surface = validator.validate_final_ivs(
                validated_surface, unfiltered_raw_iv_surface, pricing
            )

        return validated_surface


class CrossedPnLFinalIVValidator(AbstractPerExpiryFinalIVValidator):
    """
    Compares the total amount a curve is through the market, in dollar terms, to configured thresholds.

    The crossed PnL check calculates how much each curve is through the market in every
    option in vol space and multiplies this amount by vega to get a price-space measure.
    The price-space crossed PnL is summed over all options in the expiry and compared
    to configured WARN-level and FAIL-level thresholds.

    Conceptually, the crossed PnL number can be thought of as the amount of money
    we would instantaneously lose if we traded a single contract of each option at our
    fitted price, assuming the true price was actually the ask (if we bought) or bid
    (if we sold) shown in the market.
    """

    def __init__(
        self, final_iv_validation_config: VolfitterConfig.FinalIVValidationConfig
    ):
        self.final_iv_validation_config = final_iv_validation_config

    def _validate_expiry(
        self,
        final_iv_curve: FinalIVCurve,
        unfiltered_raw_iv_curve: RawIVCurve,
        pricings: Dict[Option, Pricing],
    ) -> FinalIVCurve:
        """
        Checks the total expiry crossed PnL against the configured thresholds.

        If the expiry's crossed PnL breaches the FAIL threshold, its status is set
        to FAIL. If not, but if it does breach the WARN threshold, its status is set
        to WARN.

        :param final_iv_curve: FinalIVCurve.
        :param unfiltered_raw_iv_curve: Unfiltered RawIVCurve.
        :param pricings: Dict of Pricings.
        :return: FinalIVCurve, possibly with its status set to WARN or FAIL.
        """

        if final_iv_curve.status.tag == Tag.FAIL:
            return final_iv_curve

        total_crossed_pnl = 0
        for raw_iv_point in unfiltered_raw_iv_curve.points.values():
            final_iv_point = final_iv_curve.points[raw_iv_point.option.strike]
            pricing = pricings[raw_iv_point.option]

            total_crossed_pnl += self._calc_crossed_pnl(
                raw_iv_point, final_iv_point, pricing.vega
            )

        if (
            total_crossed_pnl
            > self.final_iv_validation_config.crossed_pnl_fail_threshold
        ):
            _LOGGER.warning(
                f"Expiry {final_iv_curve.expiry} breached Crossed PnL FAIL threshold: "
                f"{total_crossed_pnl:.2f} > {self.final_iv_validation_config.crossed_pnl_fail_threshold}"
            )
            return FinalIVCurve(
                final_iv_curve.expiry,
                fail(
                    f"Crossed PnL: {total_crossed_pnl:.2f} > {self.final_iv_validation_config.crossed_pnl_fail_threshold}"
                ),
                final_iv_curve.points,
            )
        elif (
            total_crossed_pnl
            > self.final_iv_validation_config.crossed_pnl_warn_threshold
        ):
            _LOGGER.warning(
                f"Expiry {final_iv_curve.expiry} breached Crossed PnL WARN threshold: "
                f"{total_crossed_pnl:.2f} > {self.final_iv_validation_config.crossed_pnl_warn_threshold}"
            )
            return FinalIVCurve(
                final_iv_curve.expiry,
                warn(
                    f"Crossed PnL: {total_crossed_pnl:.2f} > {self.final_iv_validation_config.crossed_pnl_warn_threshold}"
                ),
                final_iv_curve.points,
            )
        else:
            return final_iv_curve

    def _calc_crossed_pnl(
        self, raw_iv_point: RawIVPoint, final_iv_point: FinalIVPoint, vega: float
    ) -> float:

        # Vega can be NaN because we are considering unfiltered raw IVs, meaning we
        # cannot assume we have filtered out options with invalid input data.
        if np.isnan(vega):
            return 0

        crossed_bid_vol = (
            max(raw_iv_point.bid_vol - final_iv_point.vol, 0)
            if np.isfinite(raw_iv_point.bid_vol)
            else 0
        )
        crossed_ask_vol = (
            max(final_iv_point.vol - raw_iv_point.ask_vol, 0)
            if np.isfinite(raw_iv_point.ask_vol)
            else 0
        )

        # At most one of crossed_bid_vol and crossed_ask_vol will be nonzero
        return (crossed_bid_vol + crossed_ask_vol) * vega
