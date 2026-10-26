"""The real client's designation-holders call, against a mocked IAM rather than the fake."""
import pytest
import responses

from fusion_auth.client import IamClient, IamUnavailable

URL = "http://iam.test/api/iam/v1/directory/holders"


@responses.activate
def test_holders_are_batched_and_unheld_posts_map_to_empty():
    responses.get(URL, json={"results": {"HOD (CSE)": [
        {"user_id": 7, "username": "h", "display_name": "Head", "kind": "faculty",
         "email": "h@x.test"}]}})
    out = IamClient().get_designation_holders(["HOD (CSE)", "Dean_s", "HOD (CSE)"])
    assert [u.user_id for u in out["HOD (CSE)"]] == [7]
    assert out["Dean_s"] == []
    assert len(responses.calls) == 1
    assert "designations=Dean_s%7CHOD+%28CSE%29" in responses.calls[0].request.url
    assert responses.calls[0].request.headers["Authorization"].startswith("Service ")


@responses.activate
def test_holders_fail_closed_on_an_outage():
    responses.get(URL, status=503)
    with pytest.raises(IamUnavailable):
        IamClient().get_designation_holders(["Director"])


def test_no_designations_means_no_call():
    assert IamClient().get_designation_holders([" ", ""]) == {}
