"""Production-engine integration tests: explicit opt-in, isolated test database."""

from .base import DATABASES as POSTGRES_DATABASES
from .test import *

DATABASES = POSTGRES_DATABASES
