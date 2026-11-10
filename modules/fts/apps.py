"""Fusion Clean Architecture - File Tracking System module configuration."""

from django.apps import AppConfig


class FtsConfig(AppConfig):
    """App config for the File Tracking System module."""

    name = "modules.fts"
    verbose_name = "File Tracking System"
