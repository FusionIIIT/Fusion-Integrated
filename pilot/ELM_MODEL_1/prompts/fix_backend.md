Fix pass (backend). These are the errors reported by the repository's own checks after the previous steps. Fix them by editing the files shown. Do not delete functionality just to silence an error.

```
### manage.py check
Traceback (most recent call last):
  File "/opt/homebrew/Cellar/python@3.12/3.12.15/Frameworks/Python.framework/Versions/3.12/lib/python3.12/importlib/__init__.py", line 90, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
  File "config/urls.py", line 18, in <module>
    path("api/v1/leave/", include("modules.leave.api.urls")),
  File "/opt/homebrew/Cellar/python@3.12/3.12.15/Frameworks/Python.framework/Versions/3.12/lib/python3.12/importlib/__init__.py", line 90, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
  File "modules/leave/api/urls.py", line 9, in <module>
    from modules.leave.api.views import (
  File "modules/leave/api/views.py", line 17, in <module>
    from modules.leave.services.applications import (
ImportError: cannot import name 'withdraw_pending_request' from 'modules.leave.services.applications' (modules/leave/services/applications.py)

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "manage.py", line 9, in <module>
    execute_from_command_line(sys.argv)
  File "/opt/homebrew/Cellar/python@3.12/3.12.15/Frameworks/Python.framework/Versions/3.12/lib/python3.12/importlib/__init__.py", line 90, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
  File "config/urls.py", line 18, in <module>
    path("api/v1/leave/", include("modules.leave.api.urls")),
  File "/opt/homebrew/Cellar/python@3.12/3.12.15/Frameworks/Python.framework/Versions/3.12/lib/python3.12/importlib/__init__.py", line 90, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
  File "modules/leave/api/urls.py", line 9, in <module>
    from modules.leave.api.views import (
  File "modules/leave/api/views.py", line 17, in <module>
    from modules.leave.services.applications import (
ImportError: cannot import name 'withdraw_pending_request' from 'modules.leave.services.applications' (modules/leave/services/applications.py)
[exit 1]
### makemigrations --check
Traceback (most recent call last):
  File "/opt/homebrew/Cellar/python@3.12/3.12.15/Frameworks/Python.framework/Versions/3.12/lib/python3.12/importlib/__init__.py", line 90, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
  File "config/urls.py", line 18, in <module>
    path("api/v1/leave/", include("modules.leave.api.urls")),
  File "/opt/homebrew/Cellar/python@3.12/3.12.15/Frameworks/Python.framework/Versions/3.12/lib/python3.12/importlib/__init__.py", line 90, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
  File "modules/leave/api/urls.py", line 9, in <module>
    from modules.leave.api.views import (
  File "modules/leave/api/views.py", line 17, in <module>
    from modules.leave.services.applications import (
ImportError: cannot import name 'withdraw_pending_request' from 'modules.leave.services.applications' (modules/leave/services/applications.py)

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "manage.py", line 9, in <module>
    execute_from_command_line(sys.argv)
  File "/opt/homebrew/Cellar/python@3.12/3.12.15/Frameworks/Python.framework/Versions/3.12/lib/python3.12/importlib/__init__.py", line 90, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
  File "config/urls.py", line 18, in <module>
    path("api/v1/leave/", include("modules.leave.api.urls")),
  File "/opt/homebrew/Cellar/python@3.12/3.12.15/Frameworks/Python.framework/Versions/3.12/lib/python3.12/importlib/__init__.py", line 90, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
  File "modules/leave/api/urls.py", line 9, in <module>
    from modules.leave.api.views import (
  File "modules/leave/api/views.py", line 17, in <module>
    from modules.leave.services.applications import (
ImportError: cannot import name 'withdraw_pending_request' from 'modules.leave.services.applications' (modules/leave/services/applications.py)
[exit 1]
### ruff errors only (F, E9)
F401 [*] `typing.Any` imported but unused
 --> modules/leave/api/serializers.py:7:20
  |
5 | """
6 |
7 | from typing import Any, Dict, List, Optional
  |                    ^^^
8 | from rest_framework import serializers
9 | from django.db.models import QuerySet
  |
help: Remove unused import
  |
6 |
  - from typing import Any, Dict, List, Optional
7 | from rest_framework import serializers
  |

F401 [*] `typing.Dict` imported but unused
 --> modules/leave/api/serializers.py:7:25
  |
5 | """
6 |
7 | from typing import Any, Dict, List, Optional
  |                         ^^^^
8 | from rest_framework import serializers
9 | from django.db.models import QuerySet
  |
help: Remove unused import
  |
6 |
  - from typing import Any, Dict, List, Optional
7 | from rest_framework import serializers
  |

F401 [*] `typing.List` imported but unused
 --> modules/leave/api/serializers.py:7:31
  |
5 | """
6 |
7 | from typing import Any, Dict, List, Optional
  |                               ^^^^
8 | from rest_framework import serializers
9 | from django.db.models import QuerySet
  |
help: Remove unused import
  |
6 |
  - from typing import Any, Dict, List, Optional
7 | from rest_framework import serializers
  |

F401 [*] `typing.Optional` imported but unused
 --> modules/leave/api/serializers.py:7:37
  |
5 | """
6 |
7 | from typing import Any, Dict, List, Optional
  |                                     ^^^^^^^^
8 | from rest_framework import serializers
9 | from django.db.models import QuerySet
  |
help: Remove unused import
  |
6 |
  - from typing import Any, Dict, List, Optional
7 | from rest_framework import serializers
  |

F401 [*] `django.db.models.QuerySet` imported but unused
  --> modules/leave/api/serializers.py:9:30
   |
 7 | from typing import Any, Dict, List, Optional
 8 | from rest_framework import serializers
 9 | from django.db.mod```
