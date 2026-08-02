"""Cursor pagination, everywhere.

Offset pagination on a table taking concurrent inserts silently skips and
duplicates rows, and COUNT(*) on a large table is a sequential scan. So there
is no `count` field by default.
"""
from rest_framework.pagination import CursorPagination as DRFCursorPagination


class CursorPagination(DRFCursorPagination):
    page_size = 25
    max_page_size = 100
    page_size_query_param = "limit"
    ordering = "-id"
