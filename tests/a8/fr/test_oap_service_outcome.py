import pytest
from django.urls import reverse
from modules.oap.models import OAPServiceOutcome

@pytest.mark.django_db
def test_oap_service_outcome_creation(oap_service_outcome_factory):
    """Test OAP Service Outcome Creation"""
    outcome = oap_service_outcome_factory()
    assert outcome is not None
    assert outcome.completed_by == outcome.user_id

@pytest.mark.django_db
def test_oap_service_outcome_update(oap_service_outcome_factory):
    """Test OAP Service Outcome Update"""
    outcome = oap_service_outcome_factory()
    new_status = "completed"
    outcome.status = new_status
    outcome.save()
    updated_outcome = OAPServiceOutcome.objects.get(id=outcome.id)
    assert updated_outcome.status == new_status

@pytest.mark.django_db
def test_oap_service_outcome_rejection(oap_service_outcome_factory):
    """Test OAP Service Outcome Rejection"""
    outcome = oap_service_outcome_factory()
    new_status = "rejected"
    outcome.status = new_status
    outcome.save()
    updated_outcome = OAPServiceOutcome.objects.get(id=outcome.id)
    assert updated_outcome.status == new_status

@pytest.mark.django_db
def test_oap_service_outcome_withdrawal(oap_service_outcome_factory):
    """Test OAP Service Outcome Withdrawal"""
    outcome = oap_service_outcome_factory()
    new_status = "withdrawn"
    outcome.status = new_status
    outcome.save()
    updated_outcome = OAPServiceOutcome.objects.get(id=outcome.id)
    assert updated_outcome.status == new_status
