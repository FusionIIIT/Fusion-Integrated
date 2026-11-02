import hashlib
import os
import pathlib
from django.conf import settings
from django.core.exceptions import ValidationError


def get_storage_root() -> pathlib.Path:
    media_root = getattr(settings, "MEDIA_ROOT", None) or os.environ.get(
        "FUSION_MEDIA_ROOT", "/tmp/fusion_media"
    )
    root = pathlib.Path(media_root) / "lms"
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def generate_storage_key(filename: str, content_bytes: bytes) -> str:
    sha256 = hashlib.sha256(content_bytes).hexdigest()
    safe_name = os.path.basename(filename).replace(" ", "_")
    return f"{sha256[:2]}/{sha256[2:4]}/{sha256}_{safe_name}"


def save_uploaded_file(filename: str, content_bytes: bytes) -> str:
    storage_key = generate_storage_key(filename, content_bytes)
    root = get_storage_root()
    target_path = root / storage_key
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "wb") as f:
        f.write(content_bytes)
    return storage_key


def get_file_path(storage_key: str) -> pathlib.Path:
    if not storage_key or ".." in storage_key or storage_key.startswith("/"):
        raise ValidationError("Invalid storage key.")
    root = get_storage_root()
    target = (root / storage_key).resolve()
    if root not in target.parents and target != root:
        raise ValidationError("Storage path escapes root.")
    if not target.exists():
        raise ValidationError("File does not exist.")
    return target
