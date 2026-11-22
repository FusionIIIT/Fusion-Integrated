import pytest
from rest_framework.test import APIClient

@pytest.fixture

def api_client(stub_iam):
    """Provide a DRF APIClient instance for tests.
    The `stub_iam` fixture ensures IAM client calls are mocked.
    """
    client = APIClient()
    # Use the fake token from FakeIam (default "tok-123") for authentication
    client.credentials(HTTP_AUTHORIZATION='tok-123')
    return client

# Expose ``make_session`` as a fixture for FR tests.
# The original ``make_session`` is defined in the root ``conftest.py`` as a helper function.
# Wrapping it in a fixture allows tests to request ``make_session`` directly.
@pytest.fixture
def make_session():
    """Return the ``make_session`` callable from the root conftest.
    Tests can then invoke ``make_session(user_id=..., ...)`` to configure the IAM session.
    """
    import importlib.util, pathlib
    root_path = pathlib.Path(__file__).resolve().parents[2] / "conftest.py"
    spec = importlib.util.spec_from_file_location("root_conftest", root_path)
    root = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(root)
    return root.make_session
