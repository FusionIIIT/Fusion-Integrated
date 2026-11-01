```python
from rest_framework.permissions import BasePermission

class _HasPhcPermission(BasePermission):
    def __init__(self, *codes):
        self.codes = codes

    def has_permission(self, request, view):
        return request.user.has_any_permission(*self.codes)

def HasPhcPermission(*codes):
    return type(f'HasPhcPermission({", ".join(codes)})', (_HasPhcPermission,), {'codes': codes})
```