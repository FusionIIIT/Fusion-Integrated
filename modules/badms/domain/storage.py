class InsufficientQuotaError(Exception):
    def __init__(self, current_usage: int, allocated_quota: int):
        super().__init__(
            f"Storage quota is full (used {current_usage} of {allocated_quota} bytes). "
            "Please delete unneeded files or submit a storage extension request."
        )
        self.current_usage = current_usage
        self.allocated_quota = allocated_quota


class QuotaNotFullError(Exception):
    def __init__(self, current_usage: int, allocated_quota: int):
        super().__init__(
            f"Storage quota is not full ({current_usage} of {allocated_quota} bytes used). "
            "Storage extension requests may only be submitted when your quota is full."
        )
        self.current_usage = current_usage
        self.allocated_quota = allocated_quota


def check_storage_quota(
    file_size_bytes: int, current_usage_bytes: int, allocated_quota_bytes: int
) -> None:
    if current_usage_bytes + file_size_bytes > allocated_quota_bytes:
        raise InsufficientQuotaError(current_usage_bytes, allocated_quota_bytes)


def validate_storage_extension_eligibility(
    current_usage_bytes: int, allocated_quota_bytes: int
) -> None:
    if current_usage_bytes < allocated_quota_bytes:
        raise QuotaNotFullError(current_usage_bytes, allocated_quota_bytes)
