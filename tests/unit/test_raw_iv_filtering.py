import datetime as dt
import numpy as np

from volfitter.domain.datamodel import Option, RawIVCurve, RawIVPoint, Pricing
from volfitter.domain.raw_iv_filtering import InTheMoneyFilter, NonTwoSidedMarketFilter


def test_in_the_money_filter_discards_ITM_calls(
    jan_expiry: dt.datetime, jan_90_call: Option, jan_100_call: Option
):
    pricing = {
        jan_90_call: _pricing_with_moneyness(jan_90_call, -1),
        jan_100_call: _pricing_with_moneyness(jan_100_call, 1),
    }
    raw_curve = RawIVCurve(
        jan_expiry,
        {
            jan_90_call: RawIVPoint(jan_90_call, 1, 2),
            jan_100_call: RawIVPoint(jan_100_call, 3, 4),
        },
    )

    victim = InTheMoneyFilter()

    filtered_curve = victim._filter_expiry(raw_curve, pricing)

    assert filtered_curve.points.keys() == {jan_100_call}


def test_in_the_money_filter_discards_ITM_puts(
    jan_expiry: dt.datetime, jan_90_put: Option, jan_100_put: Option
):
    pricing = {
        jan_90_put: _pricing_with_moneyness(jan_90_put, -1),
        jan_100_put: _pricing_with_moneyness(jan_100_put, 1),
    }
    raw_curve = RawIVCurve(
        jan_expiry,
        {
            jan_90_put: RawIVPoint(jan_90_put, 1, 2),
            jan_100_put: RawIVPoint(jan_100_put, 3, 4),
        },
    )

    victim = InTheMoneyFilter()

    filtered_curve = victim._filter_expiry(raw_curve, pricing)

    assert filtered_curve.points.keys() == {jan_90_put}


def test_non_two_sided_market_filter_discards_empty_and_one_sided_markets(
    jan_expiry: dt.datetime,
    jan_90_put: Option,
    jan_90_call: Option,
    jan_100_put: Option,
    jan_100_call: Option,
):
    raw_curve = RawIVCurve(
        jan_expiry,
        {
            jan_90_put: RawIVPoint(jan_90_put, 1, 2),
            jan_90_call: RawIVPoint(jan_90_call, np.nan, 4),
            jan_100_put: RawIVPoint(jan_100_put, 3, np.nan),
            jan_100_call: RawIVPoint(jan_100_call, np.nan, np.nan),
        },
    )

    victim = NonTwoSidedMarketFilter()

    filtered_curve = victim._filter_expiry(raw_curve, {})

    assert filtered_curve.points.keys() == {jan_90_put}


def _pricing_with_moneyness(option: Option, moneyness: float) -> Pricing:
    return Pricing(option, moneyness, 0, 0, 0, 0, 0)
