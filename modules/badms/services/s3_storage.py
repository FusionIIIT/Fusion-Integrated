"""S3 storage restricted to verified TLS 1.2 AES-256-GCM transport."""
from ssl import TLSVersion

from botocore.httpsession import URLLib3Session
from storages.backends.s3 import S3Storage

AES256_GCM_CIPHERS = (
    "ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384"
)


class AES256URLLib3Session(URLLib3Session):
    """Botocore HTTPS transport restricted to TLS 1.2 AES-256-GCM."""

    def _get_ssl_context(self):
        context = super()._get_ssl_context()
        context.minimum_version = TLSVersion.TLSv1_2
        context.maximum_version = TLSVersion.TLSv1_2
        context.set_ciphers(AES256_GCM_CIPHERS)
        return context


class AES256S3Storage(S3Storage):
    """BADMS-only S3 backend with a TLS cipher suite restriction."""

    @property
    def connection(self):
        connection = super().connection
        client = connection.meta.client
        if not isinstance(client._endpoint.http_session, AES256URLLib3Session):
            # Botocore Config lacks SSLContext support; retain endpoint verification.
            client._endpoint.http_session = AES256URLLib3Session(
                verify=self.verify,
                max_pool_connections=client.meta.config.max_pool_connections,
                timeout=(client.meta.config.connect_timeout,
                         client.meta.config.read_timeout),
            )
        return connection
