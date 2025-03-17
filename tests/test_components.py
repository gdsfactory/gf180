import pathlib

import pytest
from gdsfactory.component import Component
from gdsfactory.difftest import difftest
from pytest_regressions.data_regression import DataRegressionFixture

from gf180 import cells

skip_test = {"res_dev"}
cell_names = set(cells.keys()) - set(skip_test)
dirpath = pathlib.Path(__file__).absolute().parent / "gds_ref"


@pytest.fixture(params=cell_names, scope="function")
def component(request) -> Component:
    return cells[request.param]()


def test_pdk_gds(component: Component) -> None:
    """Avoid regressions in GDS geometry shapes and layers."""
    difftest(component, dirpath=dirpath)


def test_pdk_settings(
    component: Component, data_regression: DataRegressionFixture
) -> None:
    """Avoid regressions when exporting settings."""
    data_regression.check(component.to_dict())
