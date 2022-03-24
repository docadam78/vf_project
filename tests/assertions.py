import pytest

from volfitter.domain.datamodel import FinalIVPoint, FinalIVCurve, FinalIVSurface


def assert_point_approx_equal(
    actual: FinalIVPoint, expected: FinalIVPoint, rel=None, abs=None
):
    assert actual.expiry == expected.expiry
    assert actual.strike == expected.strike
    assert pytest.approx(expected.vol, rel=rel, abs=abs) == actual.vol


def assert_curve_approx_equal(
    actual: FinalIVCurve, expected: FinalIVCurve, rel=None, abs=None
):
    assert actual.expiry == expected.expiry
    assert actual.status == expected.status
    assert actual.points.keys() == expected.points.keys()
    for key in actual.points.keys():
        assert_point_approx_equal(actual.points[key], expected.points[key], rel, abs)


def assert_surface_approx_equal(
    actual: FinalIVSurface, expected: FinalIVSurface, rel=None, abs=None
):
    assert actual.datetime == expected.datetime
    assert actual.curves.keys() == expected.curves.keys()
    for key in actual.curves.keys():
        assert_curve_approx_equal(actual.curves[key], expected.curves[key], rel, abs)
