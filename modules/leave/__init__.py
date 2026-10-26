try:
    from .apps import LeaveConfig

    __all__ = ["LeaveConfig"]
except ImportError:
    pass
