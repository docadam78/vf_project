"""
Module that defines the datamodel classes of our domain model.
"""

import datetime as dt

from dataclasses import dataclass
from enum import auto, Enum
from typing import Dict


class OptionKind(Enum):
    CALL = auto()
    PUT = auto()


class ExerciseStyle(Enum):
    AMERICAN = auto()
    EUROPEAN = auto()


class Tag(Enum):
    OK = auto()
    WARN = auto()
    FAIL = auto()


@dataclass(frozen=True)
class Option:
    symbol: str
    expiry: dt.datetime
    strike: float
    kind: OptionKind
    exercise_style: ExerciseStyle
    contract_size: int


@dataclass(frozen=True)
class Status:
    tag: Tag
    message: str = ""


@dataclass(frozen=True)
class RawIVPoint:
    option: Option
    last_trade_date: dt.date
    bid_vol: float
    ask_vol: float


@dataclass(frozen=True)
class RawIVCurve:
    expiry: dt.datetime
    status: Status
    points: Dict[Option, RawIVPoint]


@dataclass(frozen=True)
class RawIVSurface:
    datetime: dt.datetime
    curves: Dict[dt.datetime, RawIVCurve]


@dataclass(frozen=True)
class FinalIVPoint:
    expiry: dt.datetime
    strike: float
    vol: float


@dataclass(frozen=True)
class FinalIVCurve:
    expiry: dt.datetime
    status: Status
    points: Dict[float, FinalIVPoint]


@dataclass(frozen=True)
class FinalIVSurface:
    datetime: dt.datetime
    curves: Dict[dt.datetime, FinalIVCurve]


@dataclass(frozen=True)
class ForwardCurve:
    datetime: dt.datetime
    forward_prices: Dict[dt.datetime, float]


@dataclass(frozen=True)
class Pricing:
    option: Option
    moneyness: float
    delta: float
    gamma: float
    vega: float
    theta: float
    time_to_expiry: float


@dataclass(frozen=True)
class SVIParameters:
    level: float  # "a" in Gatheral 2004
    angle: float  # "b" in Gatheral 2004
    smoothness: float  # "sigma" in Gatheral 2004
    tilt: float  # "rho" in Gatheral 2004
    center: float  # "m" in Gatheral 2004


def ok() -> Status:
    return Status(Tag.OK)


def warn(message: str) -> Status:
    return Status(Tag.WARN, message)


def fail(message: str) -> Status:
    return Status(Tag.FAIL, message)
