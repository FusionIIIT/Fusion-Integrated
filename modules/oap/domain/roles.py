"""Acting-role names as globals_designation spells them (blueprint Step 2.4)."""

HOD = "Head of Department"
ACADEMIC_ADMIN = "Academic Administrator"
DEPARTMENT_ADMIN = "Department Administrator"

#: Authority designations that verify one no-dues domain each (OA-BR-31).
#: Department, Academic Section and Student Section are absent: blueprint Gap G2.
AUTHORITY_DOMAIN = {
    "Librarian": "library",
    "Hostel Warden": "hostel",
    "Mess In-charge": "mess",
    "Lab Supervisor": "lab",
}
