"""
Module containing shared helpers for adaptors that translate OptionMetrics data.
"""

import datetime as dt


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
