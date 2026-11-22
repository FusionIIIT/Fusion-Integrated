import ssl

import pytest
from django.core.files.storage import storages
from django.test import override_settings

from modules.badms.services.s3_storage import AES256S3Storage, AES256URLLib3Session


def test_badms_tls_context_allows_only_tls12_aes256_gcm():
    context = AES256URLLib3Session()._get_ssl_context()

    assert context.minimum_version == ssl.TLSVersion.TLSv1_2
    assert context.maximum_version == ssl.TLSVersion.TLSv1_2
    assert {cipher["name"] for cipher in context.get_ciphers()
            if cipher["protocol"] == "TLSv1.2"} == {
        "ECDHE-ECDSA-AES256-GCM-SHA384",
        "ECDHE-RSA-AES256-GCM-SHA384",
    }


@pytest.mark.django_db
@override_settings(
    BADMS_STORAGE_BACKEND="s3",
    BADMS_STORAGE_PRIVATE=True,
    BADMS_STORAGE_AES256=True,
    BADMS_STORAGE_TLS=True,
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "badms": {
            "BACKEND": "modules.badms.services.s3_storage.AES256S3Storage",
            "OPTIONS": {
                "bucket_name": "test-recovery",
                "region_name": "us-east-1",
                "object_parameters": {
                    "ServerSideEncryption": "aws:kms",
                    "SSEKMSKeyId": "test-key",
                },
            },
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    },
)
def test_badms_s3_storage_does_not_replace_platform_default():
    from django.core.files.storage import FileSystemStorage

    from modules.badms.services.storage import badms_storage, require_secure_storage

    assert isinstance(storages["default"], FileSystemStorage)
    assert isinstance(badms_storage(), AES256S3Storage)
    require_secure_storage()
