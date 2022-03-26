"""
Module containing shared helpers for adapters that translate OptionMetrics data.
"""

import datetime as dt

from volfitter.domain.datamodel import OptionKind, ExerciseStyle, Option


def create_option(
    symbol: str,
    date: int,
    am_settlement: int,
    strike_price: float,
    cp_flag: str,
    exercise_style_flag: str,
    contract_size: int,
) -> Option:
    """
    Creates an Option object from data given in the OptionMetrics format.

    :param symbol: A string which contains the underlying symbol before the first
        space. In the OptionMetrics data, the symbol is actually a string
        representation of the option itself, e.g. "AMZN 200101C100000." Here we
        care only about the underlying symbol, "AMZN."
    :param date: The expiry date in YYYYMMDD format.
    :param am_settlement: 1 if expiry is at the open and 0 if expiry is at the
        close.
    :param strike_price: OptionMetrics gives the strike price multiplied by 1000,
        for unknown reasons.
    :param cp_flag: "C" if call, "P" if put.
    :param exercise_style_flag: "A" if American, "E" if European.
    :param contract_size: The contract size.
    :return: An Option object.
    """

    underlying_symbol = symbol.split()[0]
    expiry = create_expiry(date, am_settlement)
    strike = strike_price / 1000

    if cp_flag == "C":
        kind = OptionKind.CALL
    elif cp_flag == "P":
        kind = OptionKind.PUT
    else:
        raise ValueError(f"Unsupported cp_flag: {cp_flag}")

    if exercise_style_flag == "A":
        exercise_style = ExerciseStyle.AMERICAN
    elif exercise_style_flag == "E":
        exercise_style = ExerciseStyle.EUROPEAN
    else:
        raise ValueError(f"Unsupported exercise_style: {exercise_style_flag}")

    return Option(
        underlying_symbol,
        expiry,
        strike,
        kind,
        exercise_style,
        contract_size,
    )


def create_expiry(date: int, am_settlement: int) -> dt.datetime:
    """
    Creates an expiry from date and am_flag, which are in the OptionMetrics format.

    Assumes Central timezone.

    :param date: Date represented as an int in the format YYYYMMDD.
    :param am_settlement: 1 if expiry is at market open, and 0 if expiry is at
        market close.
    :return: A datetime object representing the expiry in Central timezone.
    """
    expiry = dt.datetime.strptime(str(date), "%Y%m%d")
    if am_settlement == 1:
        expiry = expiry.replace(hour=8, minute=30)
    elif am_settlement == 0:
        expiry = expiry.replace(hour=15, minute=0)
    else:
        raise ValueError(f"Unsupported am_settlement: {am_settlement}")

    return expiry
