import pytest
from django.urls import reverse
from modules.oap.models import OAPApplication

@pytest.mark.django_db
def test_create_oap_application():
    """
    Test case ID: UC-001
    Source/design reference: a8_design/UC_DESIGN.json#UC-001
    """
    url = reverse('oap_application_create')
    data = {
        'field1': 'value1',
        'field2': 'value2',
    }
    response = client.post(url, data, format='json')
    assert response.status_code == 201
    assert OAPApplication.objects.count() == 1

@pytest.mark.django_db
def test_update_oap_application():
    """
    Test case ID: UC-002
    Source/design reference: a8_design/UC_DESIGN.json#UC-002
    """
    application = OAPApplication.objects.create(field1='value1', field2='value2')
    url = reverse('oap_application_update', kwargs={'pk': application.pk})
    data = {
        'field1': 'new_value1',
        'field2': 'new_value2',
    }
    response = client.put(url, data, format='json')
    assert response.status_code == 200
    application.refresh_from_db()
    assert application.field1 == 'new_value1'
    assert application.field2 == 'new_value2'

@pytest.mark.django_db
def test_delete_oap_application():
    """
    Test case ID: UC-003
    Source/design reference: a8_design/UC_DESIGN.json#UC-003
    """
    application = OAPApplication.objects.create(field1='value1', field2='value2')
    url = reverse('oap_application_delete', kwargs={'pk': application.pk})
    response = client.delete(url)
    assert response.status_code == 204
    assert OAPApplication.objects.count() == 0