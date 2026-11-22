"""Adapter boundary for external prior-art search providers."""

from decimal import Decimal

from django.conf import settings
from django.utils.module_loading import import_string


def search_prior_art(*, query, source="", classification=""):
    """Return provider results, or None when no external provider is configured."""
    provider = getattr(settings, "PMS_PRIOR_ART_SEARCH_PROVIDER", None)
    if not provider:
        return None
    if isinstance(provider, str):
        provider = import_string(provider)
    arguments = {"query": query, "source": source}
    if classification:
        arguments["classification"] = classification
    results = provider(**arguments)
    if not isinstance(results, list):
        raise TypeError("The prior-art search provider must return a list.")
    return sorted(
        results,
        key=lambda item: Decimal(str(item.get("relevance_score") or 0)),
        reverse=True,
    )
