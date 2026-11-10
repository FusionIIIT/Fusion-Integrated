import pytest
from django.urls import reverse
from modules.oap.models import OAPServiceRequest

@pytest.mark.django_db
def test_oap_service_request_creation(oap_service_request_factory):
    """Test OAP Service Request Creation"""
    request = oap_service_request_factory()
    assert request is not None
    assert request.requested_by == request.user_id

@pytest.mark.django_db
def test_oap_service_request_update(oap_service_request_factory):
    """Test OAP Service Request Update"""
    request = oap_service_request_factory()
    new_status = "approved"
    request.status = new_status
    request.save()
    updated_request = OAPServiceRequest.objects.get(id=request.id)
    assert updated_request.status == new_status

@pytest.mark.django_db
def test_oap_service_request_rejection(oap_service_request_factory):
    """Test OAP Service Request Rejection"""
    request = oap_service_request_factory()
    new_status = "rejected"
    request.status = new_status
    request.save()
    updated_request = OAPServiceRequest.objects.get(id=request.id)
    assert updated_request.status == new_status

@pytest.mark.django_db
def test_oap_service_request_withdrawal(oap_service_request_factory):
    """Test OAP Service Request Withdrawal"""
    request = oap_service_request_factory()
    new_status = "withdrawn"
    request.status = new_status
    request.save()
    updated_request = OAPServiceRequest.objects.get(id=request.id)
    assert updated_request.status == new_status
