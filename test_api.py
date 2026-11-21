import pytest
from rest_framework.test import APIClient
from conftest import make_session
from modules.elm import services
import datetime as dt

D = dt.date
pytestmark = pytest.mark.django_db


def _client(stub_iam, **kw):
    stub_iam(make_session(**kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION='Token abc')
    return c


def test_apply_creates_application_for_caller(_client, stub_iam):
    client = _client(stub_iam, user_id=1001, permissions=('elm.leave.apply',))
    response = client.post(
        '/api/v1/elm/applications',
        json={
            'leave_type': 'CL',
            'start_date': '2026-03-02',
            'end_date': '2026-03-02'
        },
        format='json'
    )
    assert response.status_code == 201
    assert response.json()['user_id'] == 1001


def test_apply_without_permission_is_403(_client, stub_iam):
    client = _client(stub_iam, user_id=1001, permissions=())
    response = client.post(
        '/api/v1/elm/applications',
        json={
            'leave_type': 'CL',
            'start_date': '2026-03-02',
            'end_date': '2026-03-02'
        },
        format='json'
    )
    assert response.status_code == 403


def test_list_shows_only_own_applications(_client, stub_iam):
    services.submit_application(user_id=1001)
    services.submit_application(user_id=2002)
    client = _client(stub_iam, user_id=1001, permissions=('elm.leave.view',))
    response = client.get('/api/v1/elm/applications')
    assert response.status_code == 200
    assert [app['user_id'] for app in response.json()] == [1001]


def test_approve_without_permission_is_403(_client, stub_iam):
    services.submit_application(user_id=1001)
    client = _client(stub_iam, user_id=9, permissions=('elm.leave.apply',))
    response = client.post(
        '/api/v1/elm/applications/1/approve',
        format='json'
    )
    assert response.status_code == 403


def test_approver_can_approve_other_users_application(_client, stub_iam):
    services.submit_application(user_id=1001)
    client = _client(stub_iam, user_id=9, permissions=('elm.leave.approve',))
    response = client.post(
        '/api/v1/elm/applications/1/approve',
        format='json'
    )
    assert response.status_code == 200
    assert response.json()['status'] == 'APPROVED'


def test_cannot_approve_own_application_via_api(_client, stub_iam):
    services.submit_application(user_id=9)
    client = _client(stub_iam, user_id=9, permissions=('elm.leave.approve',))
    response = client.post(
        '/api/v1/elm/applications/1/approve',
        format='json'
    )
    assert response.status_code == 400


def test_approve_unknown_id_is_404(_client, stub_iam):
    client = _client(stub_iam, user_id=9, permissions=('elm.leave.approve',))
    response = client.post(
        '/api/v1/elm/applications/99999/approve',
        format='json'
    )
    assert response.status_code == 404
