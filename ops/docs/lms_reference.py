"""Generate teaching links for every live ID in the frozen LMS blueprint."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs/10-lms"
ENTRIES = {
    1: (
        "modules/lms/selectors/scoping.py",
        "def resolve_scope",
        "test_journeys.py",
        "test_uc_lms_001_access_and_uc_lms_002_manage_details",
    ),
    2: (
        "modules/lms/services/workspaces.py",
        "def update_details",
        "test_journeys.py",
        "test_uc_lms_001_access_and_uc_lms_002_manage_details",
    ),
    3: (
        "modules/lms/services/materials.py",
        "def save_material",
        "test_journeys.py",
        "test_uc_lms_003_manage_and_uc_lms_004_read_materials",
    ),
    4: (
        "modules/lms/selectors/scoping.py",
        "def materials",
        "test_journeys.py",
        "test_uc_lms_003_manage_and_uc_lms_004_read_materials",
    ),
    5: (
        "modules/lms/services/announcements.py",
        "def post_announcement",
        "test_journeys.py",
        "test_uc_lms_005_post_uc_lms_006_read_announcement_and_ta_policy",
    ),
    6: (
        "modules/lms/services/assignments.py",
        "def save_assignment",
        "test_journeys.py",
        "test_uc_lms_007_draft_uc_lms_008_publish_uc_lms_009_read_download",
    ),
    7: (
        "modules/lms/services/releases.py",
        "def change_release",
        "test_journeys.py",
        "test_uc_lms_007_draft_uc_lms_008_publish_uc_lms_009_read_download",
    ),
    8: (
        "modules/lms/services/submissions.py",
        "def create_submission",
        "test_journeys.py",
        "test_uc_lms_010_submit_uc_lms_011_own_history",
    ),
    9: (
        "modules/lms/selectors/scoping.py",
        "def submissions",
        "test_journeys.py",
        "test_uc_lms_010_submit_uc_lms_011_own_history",
    ),
    10: (
        "modules/lms/services/grading.py",
        "def save_grade",
        "test_journeys.py",
        "test_uc_lms_012_grade_uc_lms_013_release_uc_lms_014_own_grade",
    ),
    11: (
        "modules/lms/selectors/scoping.py",
        "def grades",
        "test_journeys.py",
        "test_uc_lms_012_grade_uc_lms_013_release_uc_lms_014_own_grade",
    ),
    12: (
        "modules/lms/selectors/scoping.py",
        "def grades",
        "test_journeys.py",
        "test_uc_lms_012_grade_uc_lms_013_release_uc_lms_014_own_grade",
    ),
    13: (
        "modules/lms/services/grading.py",
        "GradeAuditLog.objects.create",
        "test_journeys.py",
        "test_uc_lms_012_grade_uc_lms_013_release_uc_lms_014_own_grade",
    ),
    14: (
        "modules/lms/registry.py",
        '"lms_ta":',
        "test_privilege_escalation.py",
        "test_student_peer_and_observer_cannot_read_or_write_individual_data",
    ),
    15: (
        "modules/lms/registry.py",
        '"lms_observer":',
        "test_privilege_escalation.py",
        "test_student_peer_and_observer_cannot_read_or_write_individual_data",
    ),
}
BR = {
    1: 1,
    2: 1,
    3: 15,
    4: 14,
    5: 4,
    6: 3,
    7: 5,
    8: 5,
    9: 6,
    10: 6,
    11: 7,
    12: 8,
    13: 8,
    14: 9,
    15: 10,
    16: 11,
    17: 11,
    18: 12,
    19: 13,
}
UC = {
    1: 1,
    2: 2,
    3: 3,
    4: 4,
    5: 5,
    6: 5,
    7: 6,
    8: 7,
    9: 7,
    10: 8,
    11: 9,
    12: 10,
    13: 11,
    14: 12,
    15: 3,
}


SCHEDULED_IDS = {
    "BW-LMS-01",
    "BW-LMS-03",
    "UC-LMS-015",
    "AFR-LMS-003.3",
    "AFR-LMS-003.4",
    "AFR-LMS-007.2",
    "AFR-LMS-007.3",
}
SOURCE_OVERRIDES = {
    "CFR-LMS-001": ("modules/lms/api/views.py", "class CourseDetail("),
    "AFR-LMS-001.1": ("modules/lms/api/views.py", "class CourseDetail("),
    "AFR-LMS-001.2": ("client/src/modules/lms/pages/CoursesPage.tsx", "function Workspace("),
    "AFR-LMS-003.2": ("modules/lms/services/workspaces.py", "def save_section("),
    "AFR-LMS-005.4": ("modules/lms/selectors/scoping.py", "def announcements("),
    "UC-LMS-006": ("modules/lms/selectors/scoping.py", "def announcements("),
    "AFR-LMS-007.2": ("modules/lms/selectors/scoping.py", "def assignments("),
    "AFR-LMS-007.4": ("modules/lms/api/views.py", "class AssignmentDownload("),
    "UC-LMS-009": ("modules/lms/api/views.py", "class AssignmentDownload("),
    "BR-LMS-011": ("modules/lms/selectors/scoping.py", "def assignments("),
    "BR-LMS-006": ("modules/lms/selectors/scoping.py", "def materials("),
    "AFR-LMS-003.3": ("modules/lms/services/releases.py", "def change_release("),
    "AFR-LMS-009.2": ("client/src/modules/lms/pages/CoursesPage.tsx", "function AssignmentWork("),
    "AFR-LMS-011.1": ("modules/lms/services/grading.py", "def save_grade("),
    "AFR-LMS-011.3": ("modules/lms/services/grading.py", "def release_grade("),
    "BR-LMS-017": ("modules/lms/services/grading.py", "def release_grade("),
    "UC-LMS-013": ("modules/lms/services/grading.py", "def release_grade("),
    "AFR-LMS-012.2": ("client/src/modules/lms/pages/CoursesPage.tsx", "function ReleasedGrades("),
    "AFR-LMS-014.2": ("modules/lms/selectors/scoping.py", "def submissions("),
    "AFR-LMS-015.2": ("modules/lms/selectors/scoping.py", "def submissions("),
    "AFR-LMS-015.3": ("modules/lms/selectors/scoping.py", "def submissions("),
}
EXTRA_ENFORCEMENT = {
    "CFR-LMS-001": [("client/src/modules/lms/pages/CoursesPage.tsx", "function Workspace(")],
    "CFR-LMS-003": [
        ("modules/lms/services/workspaces.py", "def save_section("),
        ("modules/lms/services/releases.py", "def transition_content("),
    ],
    "CFR-LMS-007": [
        ("modules/lms/selectors/scoping.py", "def assignments("),
        ("modules/lms/api/views.py", "class AssignmentDownload("),
    ],
    "CFR-LMS-009": [("client/src/modules/lms/pages/CoursesPage.tsx", "function AssignmentWork(")],
    "CFR-LMS-011": [("modules/lms/services/grading.py", "def release_grade(")],
    "CFR-LMS-014": [
        ("modules/lms/services/grading.py", "def save_grade("),
        ("modules/lms/services/announcements.py", "def post_announcement("),
    ],
    "CFR-LMS-015": [("modules/lms/selectors/scoping.py", "def submissions(")],
    "BR-LMS-008": [("modules/lms/selectors/scoping.py", "def announcements(")],
    "AFR-LMS-012.2": [("modules/lms/selectors/scoping.py", "def grades(")],
    "UC-LMS-009": [("modules/lms/api/views.py", "class AssignmentDetail(")],
    "BW-LMS-02": [("modules/lms/services/releases.py", "def transition_content(")],
    "BW-LMS-03": [("modules/lms/services/submissions.py", "def create_submission(")],
    "BW-LMS-04": [("modules/lms/services/grading.py", "def release_grade(")],
    "BW-LMS-05": [("modules/lms/services/grading.py", "def release_grade(")],
    "CW-LMS-01": [("modules/lms/services/releases.py", "def transition_content(")],
    "CW-LMS-02": [("modules/lms/services/grading.py", "def release_grade(")],
}


def group_for(kind, number):
    if kind in ("CFR", "AFR"):
        return number
    return {"BR": BR, "UC": UC, "BW": {1: 3, 2: 8, 3: 8, 4: 10, 5: 10}, "CW": {1: 8, 2: 10}}[kind][
        number
    ]


def entry_for(identifier, kind, number):
    entry = ENTRIES[group_for(kind, number)]
    if identifier in SCHEDULED_IDS:
        entry = (
            "modules/lms/services/releases.py",
            "def transition_content",
            "test_http_scheduling.py",
            "test_uc_lms_015_scheduled_material_and_assignment_release",
        )
    source, anchor = SOURCE_OVERRIDES.get(identifier, entry[:2])
    return source, anchor, entry[2], entry[3]


def inventory():
    rows = []
    for line in (DOCS / "lms-blueprint.md").read_text().splitlines():
        match = re.match(r"\| ((CFR|AFR|BR|UC|BW|CW)-LMS-(\d+)(?:\.\d+)?) \| ([^|]+) \|", line)
        if match:
            identifier, kind, number, statement = match[1], match[2], int(match[3]), match[4]
            rows.append((identifier, statement, entry_for(identifier, kind, number)))
    assert len(rows) == len({row[0] for row in rows}) == 103
    return rows


def source_links(identifier, source, anchor):
    links = [(source, anchor), *EXTRA_ENFORCEMENT.get(identifier, [])]
    return "; ".join(
        f"[{path}:{line_number(path, target)}](../../{path}#L{line_number(path, target)})"
        for path, target in links
    )


def line_number(path, anchor):
    lines = (ROOT / path).read_text().splitlines()
    matches = [index for index, line in enumerate(lines, 1) if anchor in line]
    if len(matches) != 1:
        raise ValueError(f"Expected one {anchor!r} in {path}, found {len(matches)}")
    return matches[0]


def main():
    text = "# LMS implementation reference\n\n"
    text += "Links connect 103 live IDs to enforcement and builder assertions.\n\n"
    text += "| ID | Obligation | Enforcement | Builder test |\n|---|---|---|---|\n"
    for identifier, statement, (source, anchor, test_file, test_name) in inventory():
        test_path = f"modules/lms/tests/{test_file}"
        test_line = line_number(test_path, f"def {test_name}(")
        text += (
            f"| {identifier} | {statement} | "
            f"{source_links(identifier, source, anchor)} | "
            f"[{test_name}](../../{test_path}#L{test_line}) |\n"
        )
    (DOCS / "lms-reference.md").write_text(text, newline="\n")
    print("Validated 103 enforcement and test links.")


if __name__ == "__main__":
    main()
