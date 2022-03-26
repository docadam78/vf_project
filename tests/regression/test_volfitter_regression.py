import pytest

from pytest_cases import parametrize_with_cases

from tests.assertions import assert_surface_approx_equal
from tests.regression.regression_test_adapters import RegressionTestAdapter
from volfitter.composition_root import create_volfitter_service_from_adapters
from volfitter.config import VolfitterConfig
from volfitter.domain.datamodel import FinalIVSurface


@pytest.mark.regression
@pytest.mark.filterwarnings("ignore:Ill-conditioned matrix")
@parametrize_with_cases("volfitter_config, regression_test_adapter, expected_output")
def test_volfitter_regression(
    volfitter_config: VolfitterConfig,
    regression_test_adapter: RegressionTestAdapter,
    expected_output: FinalIVSurface,
):
    volfitter_service = create_volfitter_service_from_adapters(
        volfitter_config,
        regression_test_adapter,
        regression_test_adapter,
        regression_test_adapter,
        regression_test_adapter,
        regression_test_adapter,
    )

    volfitter_service.fit_full_surface()

    assert_surface_approx_equal(
        regression_test_adapter.final_iv_surface, expected_output, abs=1e-3
    )
