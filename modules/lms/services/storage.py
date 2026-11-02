import hashlib


def generate_storage_key(filename: str, content_bytes: bytes) -> str:
    sha256 = hashlib.sha256(content_bytes).hexdigest()
    return f"{sha256[:2]}/{sha256[2:4]}/{sha256}_{filename}"
