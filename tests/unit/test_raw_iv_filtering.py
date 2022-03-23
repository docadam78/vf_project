import datetime as dt
import numpy as np

from volfitter.config import VolfitterConfig
from volfitter.domain.datamodel import (
    Option,
    RawIVCurve,
    RawIVPoint,
    Pricing,
    ok,
    Tag,
    fail,
)
from volfitter.domain.raw_iv_filtering import (
    InTheMoneyFilter,
    NonTwoSidedMarketFilter,
    InsufficientValidStrikesFilter,
    StaleLastTradeDateFilter,
    WideMarketFilter,
    ExpiredExpiryFilter,
)


def test_expired_expiry_filter_marks_expired_expiry_as_warn(jan_expiry: dt.datetime):
    raw_curve = RawIVCurve(jan_expiry, ok(), {})

    victim = ExpiredExpiryFilter()

    filtered_curve = victim._filter_expiry(jan_expiry, raw_curve, {})

    assert filtered_curve.status.tag == Tag.WARN
    assert filtered_curve.status.message == "Expired."


def test_expired_expiry_filter_does_not_mark_unexpired_expiry_as_warn(
    jan_expiry: dt.datetime,
):
    raw_curve = RawIVCurve(jan_expiry, ok(), {})

    victim = ExpiredExpiryFilter()

    filtered_curve = victim._filter_expiry(
        jan_expiry - dt.timedelta(seconds=1), raw_curve, {}
    )

    assert filtered_curve == raw_curve


def test_in_the_money_filter_discards_ITM_calls(
    current_time: dt.datetime,
    jan_expiry: dt.datetime,
    jan_90_call: Option,
    jan_100_call: Option,
):
    pricing = {
        jan_90_call: _pricing_with_moneyness(jan_90_call, -1),
        jan_100_call: _pricing_with_moneyness(jan_100_call, 1),
    }
    raw_curve = RawIVCurve(
        jan_expiry,
        ok(),
        {
            jan_90_call: RawIVPoint(jan_90_call, current_time.date(), 1, 2),
            jan_100_call: RawIVPoint(jan_100_call, current_time.date(), 3, 4),
        },
    )

    victim = InTheMoneyFilter()

    filtered_curve = victim._filter_expiry(current_time, raw_curve, pricing)

    assert filtered_curve.points.keys() == {jan_100_call}


def test_in_the_money_filter_discards_ITM_puts(
    current_time: dt.datetime,
    jan_expiry: dt.datetime,
    jan_90_put: Option,
    jan_100_put: Option,
):
    pricing = {
        jan_90_put: _pricing_with_moneyness(jan_90_put, -1),
        jan_100_put: _pricing_with_moneyness(jan_100_put, 1),
    }
    raw_curve = RawIVCurve(
        jan_expiry,
        ok(),
        {
            jan_90_put: RawIVPoint(jan_90_put, current_time.date(), 1, 2),
            jan_100_put: RawIVPoint(jan_100_put, current_time.date(), 3, 4),
        },
    )

    victim = InTheMoneyFilter()

    filtered_curve = victim._filter_expiry(current_time, raw_curve, pricing)

    assert filtered_curve.points.keys() == {jan_90_put}


def test_non_two_sided_market_filter_discards_empty_and_one_sided_markets(
    current_time: dt.datetime,
    jan_expiry: dt.datetime,
    jan_90_put: Option,
    jan_90_call: Option,
    jan_100_put: Option,
    jan_100_call: Option,
):
    raw_curve = RawIVCurve(
        jan_expiry,
        ok(),
        {
            jan_90_put: RawIVPoint(jan_90_put, current_time.date(), 1, 2),
            jan_90_call: RawIVPoint(jan_90_call, current_time.date(), np.nan, 4),
            jan_100_put: RawIVPoint(jan_100_put, current_time.date(), 3, np.nan),
            jan_100_call: RawIVPoint(jan_100_call, current_time.date(), np.nan, np.nan),
        },
    )

    victim = NonTwoSidedMarketFilter()

    filtered_curve = victim._filter_expiry(current_time, raw_curve, {})

    assert filtered_curve.points.keys() == {jan_90_put}


def test_stale_last_trade_date_filter_discards_stale_markets(
    current_time: dt.datetime,
    jan_expiry: dt.datetime,
    jan_90_put: Option,
    jan_100_put: Option,
):
    config = VolfitterConfig.RawIVFilteringConfig.from_environ(
        {"RAW_IV_FILTERING_CONFIG_MAX_LAST_TRADE_AGE_DAYS": 3}
    )
    raw_curve = RawIVCurve(
        jan_expiry,
        ok(),
        {
            jan_90_put: RawIVPoint(
                jan_90_put, current_time.date() - dt.timedelta(days=1), 1, 2
            ),
            jan_100_put: RawIVPoint(
                jan_100_put, current_time.date() - dt.timedelta(days=7), 3, 4
            ),
        },
    )

    victim = StaleLastTradeDateFilter(config)

    filtered_curve = victim._filter_expiry(current_time, raw_curve, {})

    assert filtered_curve.points.keys() == {jan_90_put}


def test_wide_market_filter_discards_wide_outliers(
    current_time: dt.datetime,
    jan_expiry: dt.datetime,
    jan_90_put: Option,
    jan_100_put: Option,
    jan_110_put: Option,
):
    config = VolfitterConfig.RawIVFilteringConfig.from_environ(
        {"RAW_IV_FILTERING_CONFIG_WIDE_MARKET_OUTLIER_MAD_THRESHOLD": 0.5}
    )
    raw_curve = RawIVCurve(
        jan_expiry,
        ok(),
        {
            jan_90_put: RawIVPoint(jan_90_put, current_time.date(), 9.5, 10.5),
            jan_100_put: RawIVPoint(jan_100_put, current_time.date(), 9, 11),
            jan_110_put: RawIVPoint(jan_100_put, current_time.date(), 8, 12),
        },
    )

    victim = WideMarketFilter(config)

    filtered_curve = victim._filter_expiry(current_time, raw_curve, {})

    assert filtered_curve.points.keys() == {jan_90_put, jan_100_put}


def test_insufficient_valid_strike_filter_propagates_preexisting_failure(
    current_time: dt.datetime,
    jan_expiry: dt.datetime,
    jan_90_put: Option,
    jan_100_put: Option,
    jan_110_put: Option,
):
    config = VolfitterConfig.RawIVFilteringConfig.from_environ({})
    message = "Pre-existing failure."
    raw_curve = RawIVCurve(
        jan_expiry,
        fail(message),
        {
            jan_90_put: RawIVPoint(jan_90_put, current_time.date(), 1, 2),
            jan_100_put: RawIVPoint(jan_100_put, current_time.date(), 3, 4),
            jan_110_put: RawIVPoint(jan_100_put, current_time.date(), 5, 6),
        },
    )

    victim = InsufficientValidStrikesFilter(config)

    filtered_curve = victim._filter_expiry(current_time, raw_curve, {})

    assert filtered_curve.status.tag == Tag.FAIL
    assert filtered_curve.status.message == message


def test_insufficient_valid_strike_filter_fails_curve_with_fewer_than_three_valid_strikes(
    current_time: dt.datetime,
    jan_expiry: dt.datetime,
    jan_90_put: Option,
    jan_100_put: Option,
):
    config = VolfitterConfig.RawIVFilteringConfig.from_environ({})
    raw_curve = RawIVCurve(
        jan_expiry,
        ok(),
        {
            jan_90_put: RawIVPoint(jan_90_put, current_time.date(), 1, 2),
            jan_100_put: RawIVPoint(jan_100_put, current_time.date(), 3, 4),
        },
    )

    victim = InsufficientValidStrikesFilter(config)

    filtered_curve = victim._filter_expiry(current_time, raw_curve, {})

    assert filtered_curve.status.tag == Tag.FAIL
    assert filtered_curve.status.message == "Insufficient valid strikes."


def test_insufficient_valid_strike_filter_fails_curve_with_fewer_than_the_configured_number_of_valid_strikes(
    current_time: dt.datetime,
    jan_expiry: dt.datetime,
    jan_90_put: Option,
    jan_90_call: Option,
    jan_100_put: Option,
    jan_110_put: Option,
    jan_120_put: Option,
):
    config = VolfitterConfig.RawIVFilteringConfig.from_environ(
        {"RAW_IV_FILTERING_CONFIG_MIN_VALID_STRIKES_FRACTION": 1}
    )
    pricing = {
        jan_90_put: _pricing_with_moneyness(jan_90_put, 0),
        jan_90_call: _pricing_with_moneyness(jan_90_call, 0),
        jan_100_put: _pricing_with_moneyness(jan_100_put, 0),
        jan_110_put: _pricing_with_moneyness(jan_110_put, 0),
        jan_120_put: _pricing_with_moneyness(jan_120_put, 0),
    }
    raw_curve = RawIVCurve(
        jan_expiry,
        ok(),
        {
            jan_90_put: RawIVPoint(jan_90_put, current_time.date(), 1, 2),
            jan_100_put: RawIVPoint(jan_100_put, current_time.date(), 3, 4),
            jan_110_put: RawIVPoint(jan_110_put, current_time.date(), 5, 6),
        },
    )

    victim = InsufficientValidStrikesFilter(config)

    filtered_curve = victim._filter_expiry(current_time, raw_curve, pricing)

    assert filtered_curve.status.tag == Tag.FAIL
    assert filtered_curve.status.message == "Insufficient valid strikes."


def test_insufficient_valid_strike_filter_leaves_curve_with_enough_valid_strikes_unchanged(
    current_time: dt.datetime,
    jan_expiry: dt.datetime,
    jan_90_put: Option,
    jan_90_call: Option,
    jan_100_put: Option,
    jan_110_put: Option,
    jan_120_put: Option,
):
    config = VolfitterConfig.RawIVFilteringConfig.from_environ(
        {"RAW_IV_FILTERING_CONFIG_MIN_VALID_STRIKES_FRACTION": 0.1}
    )
    pricing = {
        jan_90_put: _pricing_with_moneyness(jan_90_put, 0),
        jan_90_call: _pricing_with_moneyness(jan_90_call, 0),
        jan_100_put: _pricing_with_moneyness(jan_100_put, 0),
        jan_110_put: _pricing_with_moneyness(jan_110_put, 0),
        jan_120_put: _pricing_with_moneyness(jan_120_put, 0),
    }
    raw_curve = RawIVCurve(
        jan_expiry,
        ok(),
        {
            jan_90_put: RawIVPoint(jan_90_put, current_time.date(), 1, 2),
            jan_100_put: RawIVPoint(jan_100_put, current_time.date(), 3, 4),
            jan_110_put: RawIVPoint(jan_110_put, current_time.date(), 5, 6),
        },
    )

    victim = InsufficientValidStrikesFilter(config)

    filtered_curve = victim._filter_expiry(current_time, raw_curve, pricing)

    assert filtered_curve == raw_curve


def _pricing_with_moneyness(option: Option, moneyness: float) -> Pricing:
    return Pricing(option, moneyness, 0, 0, 0, 0, 0)
