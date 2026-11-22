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


def inventory():
    rows = []
    for line in (DOCS / "lms-blueprint.md").read_text().splitlines():
        match = re.match(r"\| ((CFR|AFR|BR|UC|BW|CW)-LMS-(\d+)(?:\.\d+)?) \| ([^|]+) \|", line)
        if match:
            identifier, kind, number, statement = match[1], match[2], int(match[3]), match[4]
            group = (
                number
                if kind in ("CFR", "AFR")
                else (
                    BR[number]
                    if kind == "BR"
                    else UC[number]
                    if kind == "UC"
                    else {1: 3, 2: 8, 3: 8, 4: 10, 5: 10}[number]
                    if kind == "BW"
                    else {1: 8, 2: 10}[number]
                )
            )
            if (
                kind in ("BW", "CW")
                or identifier == "UC-LMS-015"
                or identifier == "BR-LMS-006"
                or identifier
                in (
                    "AFR-LMS-003.3",
                    "AFR-LMS-003.4",
                    "AFR-LMS-007.2",
                    "AFR-LMS-007.3",
                )
            ):
                entry = (
                    (
                        "modules/lms/services/releases.py",
                        "def release_one",
                        "test_journeys.py",
                        "test_uc_lms_015_scheduled_material_and_assignment_release",
                    )
                    if (
                        identifier
                        in (
                            "BW-LMS-01",
                            "BW-LMS-03",
                            "UC-LMS-015",
                            "BR-LMS-006",
                            "AFR-LMS-003.3",
                            "AFR-LMS-003.4",
                            "AFR-LMS-007.2",
                            "AFR-LMS-007.3",
                        )
                    )
                    else ENTRIES[group]
                )
            else:
                entry = ENTRIES[group]
            rows.append((identifier, statement, entry))
    assert len(rows) == len({row[0] for row in rows}) == 103
    return rows


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
        source_line = line_number(source, anchor)
        test_line = line_number(test_path, f"def {test_name}(")
        text += (
            f"| {identifier} | {statement} | "
            f"[{source}:{source_line}](../../{source}#L{source_line}) | "
            f"[{test_name}](../../{test_path}#L{test_line}) |\n"
        )
    (DOCS / "lms-reference.md").write_text(text, newline="\n")
    print("Validated 103 enforcement and test links.")


if __name__ == "__main__":
    main()
