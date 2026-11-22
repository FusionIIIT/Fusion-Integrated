MODULE = "fts"

PERMISSIONS = {
    "fts.file.view": "View file tracking records",
    "fts.file.create": "Create file tracking records",
    "fts.file.dispatch": "Dispatch files between holders",
    "fts.file.archive": "Archive file tracking records",
}

SYSTEM_PERMISSIONS: tuple[str, ...] = ()

SCOPE_PERMISSIONS: tuple[str, ...] = (
    "fts.file.view",
)

ROLE_GRANTS: dict[str, list[str]] = {
    "staff": [
        "fts.file.view",
        "fts.file.create",
        "fts.file.dispatch",
    ],
    "faculty": [
        "fts.file.view",
        "fts.file.create",
        "fts.file.dispatch",
    ],
}