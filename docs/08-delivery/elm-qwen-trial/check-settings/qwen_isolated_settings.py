from pathlib import Path
from qwen_build_settings import *
INSTALLED_APPS = [app for app in INSTALLED_APPS if app not in ("modules.placement", "devtools")]
DOMAIN_MODULES = ["modules.leave_elm"]
ROOT_URLCONF = "qwen_build_urls"
DATABASES["default"]["NAME"] = str(Path(__file__).resolve().parent / "isolated.sqlite3")
