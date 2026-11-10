import pytest
from django.urls import reverse

from modules.oap.models import OAPServiceOutcome


@pytest.mark.django_db
def test_create_oap_service_outcome():
    """
    Test case ID: UC-007
    Source/design reference: a8_design/UC_DESIGN.json#UC-007
    """
    url = reverse('oap_service_outcome_create')
    data = {
        'field1': 'value1',
        'field2': 'value2',
    }
    response = client.post(url, data, format='json')
    assert response.status_code == 201
    assert OAPServiceOutcome.objects.count() == 1

@pytest.mark.django_db
def test_update_oap_service_outcome():
    """
    Test case ID: UC-008
    Source/design reference: a8_design/UC_DESIGN.json#UC-008
    """
    outcome = OAPServiceOutcome.objects.create(field1='value1', field2='value2')
    url = reverse('oap_service_outcome_update', kwargs={'pk': outcome.pk})
    data = {
        'field1': 'new_value1',
        'field2': 'new_value2',
    }
    response = client.put(url, data, format='json')
    assert response.status_code == 200
    outcome.refresh_from_db()
    assert outcome.field1 == 'new_value1'
    assert outcome.field2 == 'new_value2'

@pytest.mark.django_db
def test_delete_oap_service_outcome():
    """
    Test case ID: UC-009
    Source/design reference: a8_design/UC_DESIGN.json#UC-009
    """
    outcome = OAPServiceOutcome.objects.create(field1='value1', field2='value2')
    url = reverse('oap_service_outcome_delete', kwargs={'pk': outcome.pk})
    response = client.delete(url)
    assert response.status_code == 204
    assert OAPServiceOutcome.objects.count() == 0