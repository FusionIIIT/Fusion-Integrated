import sys

# Ensure hostel_management alias is available for Django app registry
if "hostel_management" not in sys.modules and __name__ in sys.modules:
    sys.modules["hostel_management"] = sys.modules[__name__]

