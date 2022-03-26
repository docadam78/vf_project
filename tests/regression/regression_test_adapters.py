import datetime as dt
from typing import Collection, Dict

from volfitter.adapters.current_time_supplier import AbstractCurrentTimeSupplier
from volfitter.adapters.final_iv_consumer import AbstractFinalIVConsumer
from volfitter.adapters.forward_curve_supplier import AbstractForwardCurveSupplier
from volfitter.adapters.pricing_supplier import AbstractPricingSupplier
from volfitter.adapters.raw_iv_supplier import AbstractRawIVSupplier
from volfitter.domain.datamodel import (
    RawIVSurface,
    ForwardCurve,
    Option,
    Pricing,
    FinalIVSurface,
)


class RegressionTestAdapter(
    AbstractCurrentTimeSupplier,
    AbstractRawIVSupplier,
    AbstractForwardCurveSupplier,
    AbstractPricingSupplier,
    AbstractFinalIVConsumer,
):
    def __init__(
        self,
        current_time: dt.datetime,
        raw_iv_surface: RawIVSurface,
        forward_curve: ForwardCurve,
        pricing: Dict[Option, Pricing],
    ):
        self.current_time = current_time
        self.raw_iv_surface = raw_iv_surface
        self.forward_curve = forward_curve
        self.pricing = pricing
        self.final_iv_surface = None

    def get_current_time(self) -> dt.datetime:
        return self.current_time

    def get_raw_iv_surface(self, datetime: dt.datetime) -> RawIVSurface:
        return self.raw_iv_surface

    def get_forward_curve(
        self, datetime: dt.datetime, expiries: Collection[dt.datetime]
    ) -> ForwardCurve:
        return self.forward_curve

    def get_pricing(
        self,
        datetime: dt.datetime,
        forward_curve: ForwardCurve,
        options: Collection[Option],
    ) -> Dict[Option, Pricing]:
        return self.pricing

    def consume_final_iv_surface(self, final_iv_surface: FinalIVSurface) -> None:
        self.final_iv_surface = final_iv_surface
