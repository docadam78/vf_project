import datetime as dt
import pytest

from volfitter.domain.datamodel import Option, OptionKind, ExerciseStyle


@pytest.fixture
def current_time() -> dt.datetime:
    return dt.datetime(2022, 1, 3, 15, 0)


@pytest.fixture
def current_date(current_time: dt.datetime) -> dt.date:
    return current_time.date()


@pytest.fixture
def jan_expiry() -> dt.datetime:
    return dt.datetime(2022, 1, 21, 15, 0)


@pytest.fixture
def feb_expiry() -> dt.datetime:
    return dt.datetime(2022, 2, 18, 15, 0)


@pytest.fixture
def jan_90_call(jan_expiry) -> Option:
    return option(jan_expiry, 90, OptionKind.CALL)


@pytest.fixture
def jan_90_put(jan_expiry) -> Option:
    return option(jan_expiry, 90, OptionKind.PUT)


@pytest.fixture
def jan_100_call(jan_expiry) -> Option:
    return option(jan_expiry, 100, OptionKind.CALL)


@pytest.fixture
def jan_100_put(jan_expiry) -> Option:
    return option(jan_expiry, 100, OptionKind.PUT)


@pytest.fixture
def jan_110_call(jan_expiry) -> Option:
    return option(jan_expiry, 110, OptionKind.CALL)


@pytest.fixture
def jan_110_put(jan_expiry) -> Option:
    return option(jan_expiry, 110, OptionKind.PUT)


@pytest.fixture
def jan_120_call(jan_expiry) -> Option:
    return option(jan_expiry, 120, OptionKind.CALL)


@pytest.fixture
def jan_120_put(jan_expiry) -> Option:
    return option(jan_expiry, 120, OptionKind.PUT)


@pytest.fixture
def feb_90_call(feb_expiry) -> Option:
    return option(feb_expiry, 90, OptionKind.CALL)


@pytest.fixture
def feb_90_put(feb_expiry) -> Option:
    return option(feb_expiry, 90, OptionKind.PUT)


@pytest.fixture
def feb_100_call(feb_expiry) -> Option:
    return option(feb_expiry, 100, OptionKind.CALL)


@pytest.fixture
def feb_100_put(feb_expiry) -> Option:
    return option(feb_expiry, 100, OptionKind.PUT)


@pytest.fixture
def feb_110_call(feb_expiry) -> Option:
    return option(feb_expiry, 110, OptionKind.CALL)


@pytest.fixture
def feb_110_put(feb_expiry) -> Option:
    return option(feb_expiry, 110, OptionKind.PUT)


def option(expiry: dt.datetime, strike: float, kind: OptionKind) -> Option:
    return Option("AMZN", expiry, strike, kind, ExerciseStyle.AMERICAN, 100)
