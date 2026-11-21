import pytest
from django.urls import reverse
from modules.oap.models import OAPApplication

@pytest.mark.django_db
def test_oap_application_creation(oap_application_factory):
    """Test OAP Application Creation"""
    application = oap_application_factory()
    assert application is not None
    assert application.submitted_by == application.user_id

@pytest.mark.django_db
def test_oap_application_update(oap_application_factory):
    """Test OAP Application Update"""
    application = oap_application_factory()
    new_status = "approved"
    application.status = new_status
    application.save()
    updated_application = OAPApplication.objects.get(id=application.id)
    assert updated_application.status == new_status

@pytest.mark.django_db
def test_oap_application_rejection(oap_application_factory):
    """Test OAP Application Rejection"""
    application = oap_application_factory()
    new_status = "rejected"
    application.status = new_status
    application.save()
    updated_application = OAPApplication.objects.get(id=application.id)
    assert updated_application.status == new_status

@pytest.mark.django_db
def test_oap_application_withdrawal(oap_application_factory):
    """Test OAP Application Withdrawal"""
    application = oap_application_factory()
    new_status = "withdrawn"
    application.status = new_status
    application.save()
    updated_application = OAPApplication.objects.get(id=application.id)
    assert updated_application.status == new_status
