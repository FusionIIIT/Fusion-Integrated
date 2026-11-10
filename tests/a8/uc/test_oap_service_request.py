import pytest
from django.urls import reverse

from modules.oap.models import OAPServiceRequest


@pytest.mark.django_db
def test_create_oap_service_request():
    """
    Test case ID: UC-004
    Source/design reference: a8_design/UC_DESIGN.json#UC-004
    """
    url = reverse('oap_service_request_create')
    data = {
        'field1': 'value1',
        'field2': 'value2',
    }
    response = client.post(url, data, format='json')
    assert response.status_code == 201
    assert OAPServiceRequest.objects.count() == 1

@pytest.mark.django_db
def test_update_oap_service_request():
    """
    Test case ID: UC-005
    Source/design reference: a8_design/UC_DESIGN.json#UC-005
    """
    request = OAPServiceRequest.objects.create(field1='value1', field2='value2')
    url = reverse('oap_service_request_update', kwargs={'pk': request.pk})
    data = {
        'field1': 'new_value1',
        'field2': 'new_value2',
    }
    response = client.put(url, data, format='json')
    assert response.status_code == 200
    request.refresh_from_db()
    assert request.field1 == 'new_value1'
    assert request.field2 == 'new_value2'

@pytest.mark.django_db
def test_delete_oap_service_request():
    """
    Test case ID: UC-006
    Source/design reference: a8_design/UC_DESIGN.json#UC-006
    """
    request = OAPServiceRequest.objects.create(field1='value1', field2='value2')
    url = reverse('oap_service_request_delete', kwargs={'pk': request.pk})
    response = client.delete(url)
    assert response.status_code == 204
    assert OAPServiceRequest.objects.count() == 0