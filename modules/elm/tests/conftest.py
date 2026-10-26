import pytest

from modules.elm.tests.support import DIRECTORY


@pytest.fixture(autouse=True)
def directory(stub_iam):
    """Every ELM test sees the same small institute."""
    return stub_iam(None, users=dict(DIRECTORY))
