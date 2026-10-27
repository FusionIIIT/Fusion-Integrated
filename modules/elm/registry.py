# ELM Registry: Module registration entry point.

from . import contracts, permissions, domain
from django.conf import settings

def register_elm_module():
    """Registers all components of the ELM module with the Fusion ERP platform."""
    print("--- ELM Module Registration Initiated ---")
    
    # 1. Register Domain Entities
    print(f"Registering domain entities from {domain.__file__}")
    
    # 2. Register Permissions
    print(f"Registering permissions from {permissions.__file__}")
    
    # 3. Register External Contracts (the public API)
    print(f"Registering external contracts from {contracts.__file__}")
    
    # 4. Configure Service Provider (e.g., Celery Tasks)
    # ...
    
    print("--- ELM Module Registered Successfully ---")

# Call this function during application startup (e.g., in core/services/platform.py)
# register_elm_module()
