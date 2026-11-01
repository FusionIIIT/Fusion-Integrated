from .archive import urlpatterns as archive_urls
from .backups import urlpatterns as backup_urls
from .batches import urlpatterns as batch_urls
from .directory import urlpatterns as directory_urls
from .roles import urlpatterns as role_urls
from .schema import urlpatterns as schema_urls
from .users import urlpatterns as user_urls

urlpatterns = (
    directory_urls
    + role_urls
    + user_urls
    + schema_urls
    + backup_urls
    + batch_urls
    + archive_urls
)
