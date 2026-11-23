import pytest
import responses

from conftest import FakeIam
from fusion_auth.client import IamClient, IamUnavailable
from modules.lms.tests.conftest import KEY

BASE = "http://iam.test/api/iam/v1/academics/"


def page(rows, *, count=None, offset=0):
    return {
        "results": rows,
        "count": len(rows) if count is None else count,
        "limit": 200,
        "offset": offset,
    }


def association():
    return {
        "user_id": 2,
        "offering_key": KEY,
        "course_role": "STUDENT",
        "source_origin": "fusion_registration",
    }


@responses.activate
def test_real_course_client_consumes_every_page_and_service_authorization():
    client = IamClient()
    responses.get(BASE + "course-offerings", json=page([{"offering_key": KEY}], count=2))
    responses.get(
        BASE + "course-offerings",
        json=page([{"offering_key": "cof_" + "b" * 64}], count=2, offset=1),
    )
    assert len(client.get_course_offerings()) == 2
    assert responses.calls[0].request.headers["Authorization"] == "Service test-token"
    assert "offset=1" in responses.calls[1].request.url
    responses.get(BASE + "course-associations", json=page([association()]))
    assert client.get_course_associations([2], offering_keys=[KEY], course_role="STUDENT") == [
        association()
    ]
    assert "course_role=STUDENT" in responses.calls[2].request.url


@pytest.mark.parametrize(
    "response",
    [
        None,
        [],
        {},
        {"results": "bad"},
        page([], count=-1),
        page([], count=2),
        page([{"offering_key": "bad"}]),
        page([{"offering_key": "cof_" + "z" * 64}]),
        page([{"offering_key": KEY}], count=0),
        page([], count="0"),
    ],
)
@responses.activate
def test_malformed_course_response_never_becomes_membership(response):
    responses.get(BASE + "course-offerings", json=response)
    with pytest.raises(IamUnavailable):
        IamClient().get_course_offerings()


@pytest.mark.parametrize("status", [401, 403, 404, 400, 500, 503])
@responses.activate
def test_iam_errors_fail_closed(status):
    responses.get(BASE + "course-offerings", status=status)
    with pytest.raises(IamUnavailable):
        IamClient().get_course_offerings()


@responses.activate
def test_bad_association_fields_are_rejected():
    for change in ({"user_id": "2"}, {"course_role": "ADMIN"}, {"source_origin": "invented"}):
        responses.get(BASE + "course-associations", json=page([{**association(), **change}]))
        with pytest.raises(IamUnavailable):
            IamClient().get_course_associations([2])


@responses.activate
def test_empty_filters_make_no_network_calls_and_large_offering_filters_are_batched():
    client = IamClient()
    assert client.get_course_offerings([]) == []
    assert client.get_course_associations([]) == []
    assert client.get_course_associations([2], offering_keys=[]) == []
    with pytest.raises(ValueError):
        client.get_course_associations(range(501))
    for _ in range(4):
        responses.get(BASE + "course-offerings", json=page([]))
    keys = ["cof_" + f"{index:064x}" for index in range(201)]
    assert client.get_course_offerings(keys) == []
    assert len(responses.calls) == 2


def test_fake_client_keeps_the_real_course_method_signature():
    import inspect

    for name in ("get_course_offerings", "get_course_associations"):
        assert inspect.signature(getattr(FakeIam, name)) == inspect.signature(
            getattr(IamClient, name)
        )
