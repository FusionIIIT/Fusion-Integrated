import logging
from datetime import datetime

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ..models import Batch, Curriculum, Discipline, Student, StudentBatchUpload

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    def __init__(self, payload, status=400):
        super().__init__(payload.get("message", "Service error"))
        self.payload = payload
        self.status = status


def sanitize_phone_number(value):
    if value is None:
        return value
    text = str(value)
    return text[:-2] if text.endswith(".0") else text


def sanitize_rank_value(value):
    if value in (None, "", "null"):
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text[:-2] if text.endswith(".0") else text


def safe_int(value):
    if value in (None, "", "null"):
        return None
    try:
        text = str(value).replace(",", "").strip()
        return int(text) if text.isdigit() else None
    except (ValueError, TypeError):
        return None


def parse_date_flexible(value):
    if value in (None, ""):
        return None
    if hasattr(value, "date"):
        return value.date()
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y", "%d-%m-%y", "%d/%m/%y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def validate_phone_numbers(student):
    student_fields = ["phone_number", "Mobile No", "phoneNumber"]
    father_fields = ["father_mobile", "Father Mobile Number", "fatherMobile"]
    errors = []

    def pick(fields):
        for field in fields:
            if student.get(field):
                return student.get(field)
        return None

    def clean(raw):
        value = sanitize_phone_number(raw)
        return value.replace(" ", "").replace("-", "") if value else None

    student_phone = clean(pick(student_fields))
    father_phone = clean(pick(father_fields))

    if student_phone and (not student_phone.isdigit() or len(student_phone) != 10):
        errors.append(f"Invalid student mobile: {student_phone}")
    if father_phone and (not father_phone.isdigit() or len(father_phone) != 10):
        errors.append(f"Invalid father mobile: {father_phone}")
    if student_phone and father_phone and student_phone == father_phone:
        errors.append("Father's mobile number should not be same as student's mobile number")

    return student_phone, father_phone, errors


def get_academic_year_from_batch_year(batch_year):
    batch_year = int(batch_year)
    return f"{batch_year}-{str(batch_year + 1)[-2:]}"


def current_academic_year():
    now = datetime.now()
    batch_year = now.year if now.month >= 7 else now.year - 1
    return batch_year, get_academic_year_from_batch_year(batch_year)


def normalize_year_input(year_input):
    if isinstance(year_input, str) and "-" in year_input:
        parts = year_input.split("-")
        if len(parts) != 2:
            raise ValueError(f"Invalid academic year format: {year_input}")
        batch_year = int(parts[0])
        if int(parts[1]) != (batch_year + 1) % 100:
            raise ValueError(f"Invalid academic year format: {year_input}")
        return batch_year, year_input
    batch_year = int(year_input)
    return batch_year, get_academic_year_from_batch_year(batch_year)


def resolve_year(selected_year):
    if not selected_year:
        return current_academic_year()
    try:
        return normalize_year_input(selected_year)
    except (ValueError, TypeError) as exc:
        raise ServiceError({"success": False, "message": f"Invalid year format: {exc}"})


def require_curriculum(action):
    if not Curriculum.objects.filter(working_curriculum=True).exists():
        raise ServiceError({
            "success": False,
            "message": f"CURRICULUM REQUIRED: No working curriculums found. Please create a curriculum first before {action}.",
            "validation_error": "missing_curriculum",
        })


def require_batches(batch_year, academic_year, action):
    batches = Batch.objects.filter(year=batch_year, running_batch=True)
    if not batches.exists():
        raise ServiceError({
            "success": False,
            "message": f"BATCH REQUIRED: No active batches found for academic year {academic_year}. Please create batches with assigned curriculums first before {action}.",
            "validation_error": "missing_batch",
            "academic_year": academic_year,
            "batch_year": batch_year,
        })
    without_curriculum = batches.filter(curriculum__isnull=True)
    if without_curriculum.exists():
        names = [f"{b.name} {b.discipline.acronym}" for b in without_curriculum]
        raise ServiceError({
            "success": False,
            "message": f'These batches for {academic_year} have no curriculum assigned: {", ".join(names)}. Assign a curriculum to all batches first.',
            "validation_error": "batch_missing_curriculum",
            "batches_without_curriculum": names,
        })


DISPLAY_BRANCH = {
    "Computer Science and Engineering": "CSE",
    "Electronics and Communication Engineering": "ECE",
    "Mechanical Engineering": "ME",
    "Smart Manufacturing": "SM",
    "Design": "DES",
}

DISCIPLINE_ACRONYM = {
    "Computer Science and Engineering": "CSE",
    "Electronics and Communication Engineering": "ECE",
    "Mechanical Engineering": "ME",
    "Smart Manufacturing": "SM",
    "Design": "Des.",
    "Mechatronics": "MT",
}

DISCIPLINE_ALIASES = {
    "computer science and engineering": "Computer Science and Engineering",
    "electronics and communication engineering": "Electronics and Communication Engineering",
    "mechanical engineering": "Mechanical Engineering",
    "smart manufacturing": "Smart Manufacturing",
    "design": "Design",
    "mechatronics": "Mechatronics",
}


def display_branch_name(discipline):
    return DISPLAY_BRANCH.get(discipline, discipline)


def batch_name_from_discipline(discipline_name, programme_type):
    is_design = "design" in (discipline_name or "").lower()
    if programme_type == "ug":
        return "B.Des" if is_design else "B.Tech"
    if programme_type == "pg":
        return "M.Des" if is_design else "M.Tech"
    return programme_type.upper()


def get_or_create_discipline(discipline_name):
    normalized = (discipline_name or "").strip()
    lower = normalized.lower()
    canonical = next((v for k, v in DISCIPLINE_ALIASES.items() if k in lower), normalized)
    discipline = Discipline.objects.filter(name=canonical).first()
    if discipline:
        return discipline
    return Discipline.objects.create(name=canonical, acronym=DISCIPLINE_ACRONYM.get(canonical, canonical[:10]))


def available_curriculums(batch):
    if not batch:
        return []
    if batch.curriculum_options:
        return batch.curriculum_options
    if batch.name in ("M.Tech", "M.Des", "Phd") and not batch.curriculum:
        curriculums = Curriculum.objects.filter(working_curriculum=True, programme__name__icontains=batch.name)
        return [{"id": c.id, "name": c.name, "version": c.version} for c in curriculums]
    if batch.curriculum:
        return [{"id": batch.curriculum.id, "name": batch.curriculum.name, "version": batch.curriculum.version}]
    return []


def curriculum_display(batch):
    options = available_curriculums(batch)
    if len(options) > 1:
        names = [o["name"] for o in options]
        return f"{len(names)} curriculums: {', '.join(names)}"
    if len(options) == 1:
        return options[0]["name"]
    if batch.curriculum:
        return batch.curriculum.name
    return "No curriculum assigned"


def filled_seats(batch):
    try:
        return Student.objects.filter(batch_id=batch).count() if batch.curriculum else 0
    except Exception:
        return 0


def branch_code(branch_name, programme_type):
    lower = (branch_name or "").lower()
    prefix = {"ug": "B", "pg": "M", "phd": "P"}.get(programme_type, "U")
    if "computer" in lower or "cse" in lower:
        return prefix + "CS"
    if "electronics" in lower or "ece" in lower:
        return prefix + "EC"
    if "mechanical" in lower or "me" in lower:
        return prefix + "ME"
    if "smart" in lower or "manufacturing" in lower:
        return prefix + "SM"
    if "design" in lower:
        return prefix + "DS"
    return "UNK"


def allocate(students, programme_type, batch_year):
    groups = {}
    for student in students:
        branch_field = student.get("Discipline") or student.get("branch", "")
        code = branch_code(branch_field, programme_type)
        groups.setdefault(code, []).append({
            **student,
            "branch_code": code,
            "display_branch": display_branch_name(branch_field),
        })
    for code in groups:
        groups[code].sort(key=lambda s: s.get("Name") or s.get("name", ""))

    processed = []
    for code, members in groups.items():
        for student in members:
            processed.append({
                **student,
                "roll_number": student.get("Institute Roll Number") or student.get("rollNumber", ""),
                "institute_email": student.get("Institute Email ID") or student.get("instituteEmail", ""),
                "year": batch_year,
                "programme": programme_type.upper(),
                "reported_status": "NOT_REPORTED",
            })
    processed.sort(key=lambda s: s["roll_number"] or "")
    return processed


def allocation_summary(students, programme_type):
    counts = {}
    for student in students:
        code = student.get("branch_code", "Unknown")
        counts[code] = counts.get(code, 0) + 1
    return {"total_students": len(students), "branch_counts": counts, "programme": programme_type.upper()}


def is_duplicate(student, fields):
    mapping = {
        "jeeAppNo": ("jee_app_no", "JEE Application Number"),
        "rollNumber": ("roll_number", "Roll Number"),
        "instituteEmail": ("institute_email", "Institute Email"),
        "personalEmail": ("personal_email", "Personal Email"),
    }
    for field in fields:
        column, label = mapping.get(field, (field.lower(), field))
        value = student.get(field)
        if not value:
            continue
        existing = StudentBatchUpload.objects.filter(**{column: value}).first()
        if existing:
            return True, f"{label} {value} already exists for {existing.name}"
    return False, ""


def serialize_student(student):
    def safe_get(attr, default=""):
        try:
            val = getattr(student, attr, None)
            if attr.endswith("_date") and val and hasattr(val, "isoformat"):
                return val.isoformat()
            return val or default
        except Exception:
            return default

    try:
        return {
            "id": student.id,
            "name": safe_get("name", ""),
            "roll_number": safe_get("roll_number"),
            "institute_email": safe_get("institute_email"),
            "jee_app_no": safe_get("jee_app_no"),
            "father_name": safe_get("father_name", ""),
            "mother_name": safe_get("mother_name", ""),
            "gender": safe_get("gender", ""),
            "category": safe_get("category", ""),
            "pwd": safe_get("pwd", "NO"),
            "minority": safe_get("minority"),
            "date_of_birth": safe_get("date_of_birth"),
            "phone_number": safe_get("phone_number"),
            "address": safe_get("address", ""),
            "state": safe_get("state"),
            "branch": safe_get("branch", ""),
            "section": safe_get("section"),
            "specialization": safe_get("specialization"),
            "ai_rank": safe_get("ai_rank"),
            "category_rank": safe_get("category_rank"),
            "father_occupation": safe_get("father_occupation"),
            "father_mobile": safe_get("father_mobile"),
            "mother_occupation": safe_get("mother_occupation"),
            "mother_mobile": safe_get("mother_mobile"),
            "aadhar_number": safe_get("aadhar_number"),
            "allotted_category": safe_get("allotted_category"),
            "allotted_gender": safe_get("allotted_gender"),
            "parent_email": safe_get("parent_email"),
            "personal_email": safe_get("personal_email"),
            "country": safe_get("country", ""),
            "nationality": safe_get("nationality", ""),
            "blood_group": safe_get("blood_group"),
            "blood_group_remarks": safe_get("blood_group_remarks"),
            "pwd_category": safe_get("pwd_category"),
            "pwd_category_remarks": safe_get("pwd_category_remarks"),
            "admission_mode": safe_get("admission_mode"),
            "admission_mode_remarks": safe_get("admission_mode_remarks"),
            "income_group": safe_get("income_group"),
            "income": str(safe_get("income")) if safe_get("income") else "",
            "tenth_marks": safe_get("tenth_marks"),
            "twelfth_marks": safe_get("twelfth_marks"),
            "year": safe_get("year"),
            "academic_year": safe_get("academic_year", ""),
            "programme_type": safe_get("programme_type", ""),
            "allocation_status": safe_get("allocation_status", ""),
            "reported_status": safe_get("reported_status", "NOT_REPORTED"),
            "status_display": dict(StudentBatchUpload.REPORTED_STATUS_CHOICES).get(
                safe_get("reported_status", "NOT_REPORTED"), "Unknown"
            ),
            "source": safe_get("source", ""),
        }
    except Exception as e:
        logger.error(f"Failed to serialize StudentBatchUpload {getattr(student, 'id', '?')}: {e}")
        raise


STUDENT_FIELD_MAP = {
    "jeeAppNo": "jee_app_no", "rollNumber": "roll_number", "instituteEmail": "institute_email",
    "fname": "father_name", "fatherName": "father_name", "mname": "mother_name", "motherName": "mother_name",
    "dob": "date_of_birth", "dateOfBirth": "date_of_birth", "phoneNumber": "phone_number",
    "email": "personal_email", "alternateEmail": "personal_email", "parentEmail": "parent_email",
    "jeeRank": "ai_rank", "aiRank": "ai_rank", "categoryRank": "category_rank",
    "tenthMarks": "tenth_marks", "twelfthMarks": "twelfth_marks",
    "fatherOccupation": "father_occupation", "fatherMobile": "father_mobile",
    "motherOccupation": "mother_occupation", "motherMobile": "mother_mobile",
    "allottedCategory": "allotted_category", "allottedGender": "allotted_gender",
    "bloodGroup": "blood_group", "bloodGroupRemarks": "blood_group_remarks",
    "pwdCategory": "pwd_category", "pwdCategoryRemarks": "pwd_category_remarks",
    "admissionMode": "admission_mode", "admissionModeRemarks": "admission_mode_remarks",
    "incomeGroup": "income_group", "aadharNumber": "aadhar_number", "reportedStatus": "reported_status",
}

DIRECT_STUDENT_FIELDS = {
    "name", "gender", "category", "pwd", "minority", "address", "state", "branch", "specialization",
    "jee_app_no", "roll_number", "institute_email", "father_name", "mother_name", "personal_email",
    "parent_email", "phone_number", "country", "nationality", "blood_group", "blood_group_remarks",
    "pwd_category", "pwd_category_remarks", "admission_mode", "admission_mode_remarks", "income_group",
    "income", "father_occupation", "father_mobile", "mother_occupation", "mother_mobile",
    "allotted_category", "allotted_gender", "aadhar_number", "reported_status",
}
INT_STUDENT_FIELDS = {"ai_rank", "category_rank"}
FLOAT_STUDENT_FIELDS = {"tenth_marks", "twelfth_marks"}


def get_student(student_id):
    student = StudentBatchUpload.objects.filter(id=student_id).first()
    if not student:
        raise ServiceError({"success": False, "message": "Student not found"}, status=404)
    return {"success": True, "student": serialize_student(student)}


def update_student(student_id, data):
    student = StudentBatchUpload.objects.filter(id=student_id).first()
    if not student:
        raise ServiceError({"success": False, "message": "Student not found"}, status=404)

    resolved = {}
    for key, value in data.items():
        field = STUDENT_FIELD_MAP.get(key, key)
        if field in DIRECT_STUDENT_FIELDS or field in INT_STUDENT_FIELDS or field in FLOAT_STUDENT_FIELDS or field == "date_of_birth":
            resolved[field] = value

    for column, label in (("jee_app_no", "JEE Application Number"), ("roll_number", "Roll Number"), ("institute_email", "Institute Email")):
        val = resolved.get(column)
        if val and val != getattr(student, column) and StudentBatchUpload.objects.filter(**{column: val}).exclude(id=student_id).exists():
            raise ServiceError({"success": False, "message": f"{label} {val} already exists for another student"})

    for field, value in resolved.items():
        if field == "date_of_birth":
            student.date_of_birth = parse_date_flexible(value)
        elif field in INT_STUDENT_FIELDS:
            setattr(student, field, safe_int(sanitize_rank_value(value)))
        elif field in FLOAT_STUDENT_FIELDS:
            try:
                setattr(student, field, float(value) if value not in (None, "", "null") else None)
            except (ValueError, TypeError):
                setattr(student, field, None)
        elif field == "income":
            student.income = value or None
        else:
            setattr(student, field, value)

    student.save()
    return {"success": True, "student": serialize_student(student), "message": "Student updated successfully."}


def delete_student(student_id):
    from django.db import connection

    student = StudentBatchUpload.objects.filter(id=student_id).first()
    if not student:
        raise ServiceError({"success": False, "message": "Student not found"}, status=404)
    name = student.name
    with transaction.atomic():
        # Clear rows that reference this student so the FK constraints don't block the delete.
        with connection.cursor() as cursor:
            for table in ("password_email_log", "student_password_history", "programme_curriculum_studentstatuslog"):
                try:
                    cursor.execute(f"DELETE FROM {table} WHERE student_id = %s", [student_id])
                except Exception:
                    pass
        student.delete()
    return {"success": True, "message": f"Student {name} deleted successfully."}


def update_student_status(student_id, status):
    valid = {choice[0] for choice in StudentBatchUpload.REPORTED_STATUS_CHOICES}
    if status not in valid:
        raise ServiceError({"success": False, "message": f"Invalid status. Allowed: {', '.join(sorted(valid))}"})
    student = StudentBatchUpload.objects.filter(id=student_id).first()
    if not student:
        raise ServiceError({"success": False, "message": "Student not found"}, status=404)
    student.reported_status = status
    student.save()
    return {"success": True, "student": serialize_student(student), "message": "Status updated."}


def list_disciplines():
    return {
        "success": True,
        "disciplines": [
            {"id": d.id, "name": d.name, "acronym": d.acronym}
            for d in Discipline.objects.all().order_by("name")
        ],
    }


def list_curriculums():
    return {
        "success": True,
        "curriculums": [
            {"id": c.id, "name": c.name, "version": str(c.version), "programme": c.programme.name}
            for c in Curriculum.objects.filter(working_curriculum=True).select_related("programme").order_by("name")
        ],
    }


def sync_batches():
    batches = Batch.objects.filter(running_batch=True).select_related("discipline", "curriculum").order_by("year", "discipline__name")
    results = []
    for batch in batches:
        actual_filled = filled_seats(batch)
        total = batch.total_seats or 0
        results.append({
            "batch_id": batch.id,
            "name": batch.name,
            "discipline": batch.discipline.acronym,
            "discipline_name": batch.discipline.name,
            "year": batch.year,
            "total_seats": total,
            "filled_seats": actual_filled,
            "available_seats": max(0, total - actual_filled),
            "curriculum": curriculum_display(batch),
            "curriculum_id": batch.curriculum.id if batch.curriculum else None,
            "status": "READY",
        })
    return {"success": True, "batches": results, "total_batches": len(results)}


def batch_students(batch_id, specialization=None):
    batch = Batch.objects.filter(id=batch_id).select_related("discipline", "curriculum").first()
    if not batch:
        raise ServiceError({"success": False, "message": f"Batch with ID {batch_id} not found"}, status=404)

    programme_type = "ug" if batch.name.startswith("B.") else "pg" if batch.name.startswith("M.") else "phd"
    students = StudentBatchUpload.objects.filter(year=batch.year, programme_type=programme_type).defer("section")

    discipline = batch.discipline
    if programme_type == "pg" and specialization:
        students = students.filter(specialization__icontains=specialization)
    elif discipline is not None:
        discipline_name = discipline.name
        discipline_filter = Q(branch__icontains=discipline_name)
        if "Computer Science" in discipline_name:
            discipline_filter |= Q(branch__icontains="CSE") | Q(branch__icontains="Computer Science")
        elif "Electronics" in discipline_name:
            discipline_filter |= Q(branch__icontains="ECE") | Q(branch__icontains="Electronics")
        elif "Mechanical" in discipline_name:
            discipline_filter |= Q(branch__icontains="ME") | Q(branch__icontains="Mechanical")
        students = students.filter(discipline_filter)

    try:
        rows = []
        for student in students.order_by("roll_number"):
            try:
                rows.append(serialize_student(student))
            except Exception:
                logger.exception("Skipping unserializable student in batch %s", batch_id)
    except Exception as exc:
        # Surface the underlying DB/query error (e.g. a schema mismatch on the
        # ERP table) instead of a generic 500, so it is actionable to the operator.
        raise ServiceError({"success": False, "message": f"Failed to fetch students: {exc}"}, status=500) from exc

    return {
        "success": True,
        "batch": {
            "id": batch.id,
            "name": batch.name,
            "discipline": discipline.acronym if discipline else None,
            "year": batch.year,
            "curriculum": batch.curriculum.name if batch.curriculum else None,
        },
        "students": rows,
        "total_students": len(rows),
    }


def create_batch(data):
    programme = data.get("programme") or data.get("batch_name")
    discipline_id = data.get("discipline")
    year = data.get("year") or data.get("batchYear")
    total_seats = data.get("total_seats") or data.get("totalSeats")
    curriculum_data = data.get("curriculum") or data.get("curriculum_id")
    specialization = data.get("specialization", "")

    missing = [name for name, value in (
        ("programme", programme), ("discipline", discipline_id), ("year", year), ("total_seats", total_seats),
    ) if not value]
    if missing:
        raise ServiceError({"success": False, "message": f'Missing required fields: {", ".join(missing)}'})

    curriculum_obj = None
    if curriculum_data and str(curriculum_data) not in ("null", "undefined", ""):
        curriculum_id = curriculum_data[0] if isinstance(curriculum_data, list) and curriculum_data else curriculum_data
        try:
            curriculum_obj = Curriculum.objects.get(id=int(curriculum_id), working_curriculum=True)
        except (Curriculum.DoesNotExist, ValueError, TypeError):
            raise ServiceError({"success": False, "message": f"Invalid curriculum ID: {curriculum_id}.", "validation_error": "invalid_curriculum"})

    discipline_obj = Discipline.objects.filter(id=discipline_id).first()
    if not discipline_obj:
        raise ServiceError({"success": False, "message": f"Invalid discipline ID: {discipline_id}"})

    try:
        year = int(year)
        total_seats = int(total_seats)
    except (ValueError, TypeError):
        raise ServiceError({"success": False, "message": "Year and total_seats must be integers"})

    if Batch.objects.filter(name=programme, discipline=discipline_obj, year=year, running_batch=True).exists():
        raise ServiceError({"success": False, "message": f"Batch \"{programme}\" already exists for {discipline_obj.acronym} {year}", "validation_error": "duplicate_batch"})

    batch = Batch.objects.create(
        name=programme, discipline=discipline_obj, year=year,
        curriculum=curriculum_obj, total_seats=total_seats, running_batch=True,
    )
    return {
        "success": True,
        "data": {
            "id": batch.id,
            "programme": batch.name,
            "discipline": batch.discipline.name,
            "disciplineAcronym": batch.discipline.acronym,
            "year": batch.year,
            "total_seats": batch.total_seats,
            "totalSeats": batch.total_seats,
            "specialization": specialization,
            "running_batch": batch.running_batch,
            "curriculum": curriculum_obj.name if curriculum_obj else None,
            "curriculum_id": curriculum_obj.id if curriculum_obj else None,
        },
        "message": "Batch created successfully" + (f" with curriculum: {curriculum_obj.name}" if curriculum_obj else " (no curriculum assigned)"),
    }


def delete_batch(batch_id):
    batch = Batch.objects.filter(id=batch_id).select_related("discipline", "curriculum").first()
    if not batch:
        raise ServiceError({"success": False, "message": f"Batch with ID {batch_id} not found"}, status=404)

    uploaded = StudentBatchUpload.objects.filter(year=batch.year, branch__icontains=batch.discipline.name).count()
    academic = Student.objects.filter(batch_id=batch).count()
    total = uploaded + academic
    if total > 0:
        raise ServiceError({
            "success": False,
            "message": f'Cannot delete batch "{batch.name} {batch.discipline.acronym} {batch.year}". It contains {total} students. Transfer or remove students first.',
            "student_count": total,
            "validation_error": "batch_has_students",
        })

    info = {"id": batch.id, "name": batch.name, "discipline": batch.discipline.acronym, "year": batch.year}
    batch.delete()
    return {"success": True, "message": f'Successfully deleted batch "{info["name"]} {info["discipline"]} {info["year"]}".', "deleted_batch": info}


def save_students(data):
    students = data.get("students", [])
    programme_type = data.get("programme_type", "ug")
    batch_year, academic_year = resolve_year(data.get("academic_year"))
    require_curriculum("saving student data")
    require_batches(batch_year, academic_year, "saving student data")

    if not students:
        raise ServiceError({"success": False, "message": "No student data provided"})

    skip_duplicates = data.get("skip_duplicates", False)
    duplicate_fields = data.get("duplicate_check_fields", ["jeeAppNo", "rollNumber", "instituteEmail"])

    successful = failed = skipped_duplicates = skipped_invalid = validation_errors = 0
    errors = []

    if skip_duplicates:
        kept = []
        for student in students:
            duplicate, _ = is_duplicate(student, duplicate_fields)
            if duplicate:
                skipped_duplicates += 1
            else:
                kept.append(student)
        students = kept

    valid = []
    for student in students:
        _, _, phone_errors = validate_phone_numbers(student)
        if phone_errors:
            skipped_invalid += 1
            errors.append(f"Skipped {student.get('Name', 'Unknown')}: {'; '.join(phone_errors)}")
        else:
            valid.append(student)

    processed = allocate(valid, programme_type, batch_year)

    for student_data in processed:
        name = (student_data.get("Name") or student_data.get("name", "")).strip()
        if not name:
            validation_errors += 1
            errors.append("Student has no name - skipping")
            continue

        discipline_name = student_data.get("Discipline") or student_data.get("branch", "")
        specialization = student_data.get("Specialization") or student_data.get("specialization", "")

        if programme_type == "pg" and specialization:
            if "design" in discipline_name.lower():
                batch_name = "M.Des"
            elif specialization == "Mechatronics":
                batch_name = "M.Tech"
            else:
                batch_name = f"M.Tech {specialization}"
        else:
            batch_name = batch_name_from_discipline(discipline_name, programme_type)

        discipline_obj = get_or_create_discipline(discipline_name)
        batch_obj = Batch.objects.filter(name=batch_name, discipline=discipline_obj, year=batch_year, running_batch=True).first()
        if not batch_obj:
            failed += 1
            errors.append({
                "student": name,
                "roll_number": student_data.get("Institute Roll Number", ""),
                "error": f"No active batch exists for {batch_name} with discipline '{discipline_obj.name}' in Year-{batch_year}. Create the batch first.",
                "validation_error": "missing_batch",
            })
            continue

        try:
            with transaction.atomic():
                StudentBatchUpload.objects.create(
                    jee_app_no=student_data.get("JEE App. No./CCMT Roll. No.") or student_data.get("jee_app_no") or student_data.get("jeeAppNo") or None,
                    roll_number=student_data.get("Institute Roll Number") or student_data.get("rollNumber") or None,
                    institute_email=student_data.get("Institute Email ID") or student_data.get("instituteEmail", ""),
                    name=name,
                    father_name=student_data.get("Father's Name") or student_data.get("fname", ""),
                    mother_name=student_data.get("Mother's Name") or student_data.get("mname", ""),
                    gender=student_data.get("Gender") or student_data.get("gender", ""),
                    category=student_data.get("Category") or student_data.get("category", ""),
                    pwd=student_data.get("PWD") or student_data.get("pwd", "NO"),
                    minority=student_data.get("Minority") or student_data.get("minority", ""),
                    phone_number=sanitize_phone_number(student_data.get("Mobile No") or student_data.get("phoneNumber", "")),
                    personal_email=student_data.get("Alternate Email ID") or student_data.get("alternateEmail", "") or student_data.get("personal_email", ""),
                    parent_email=student_data.get("Parent Email") or student_data.get("parentEmail", ""),
                    address=student_data.get("Full Address") or student_data.get("address", ""),
                    state=student_data.get("State") or student_data.get("state", ""),
                    country=student_data.get("Country") or student_data.get("country", "India"),
                    nationality=student_data.get("Nationality") or student_data.get("nationality", "Indian"),
                    blood_group=student_data.get("Blood Group") or student_data.get("bloodGroup", ""),
                    blood_group_remarks=student_data.get("Blood Group Remarks") or student_data.get("bloodGroupRemarks", ""),
                    pwd_category=student_data.get("PwD Category") or student_data.get("pwdCategory", ""),
                    pwd_category_remarks=student_data.get("PwD Category Remarks") or student_data.get("pwdCategoryRemarks", ""),
                    admission_mode=student_data.get("Admission Mode") or student_data.get("admissionMode", ""),
                    admission_mode_remarks=student_data.get("Admission Mode Remarks") or student_data.get("admissionModeRemarks", ""),
                    income_group=student_data.get("Income Group") or student_data.get("incomeGroup", ""),
                    income=student_data.get("Income") or student_data.get("income") or None,
                    branch=student_data.get("Discipline") or student_data.get("branch", ""),
                    specialization=specialization,
                    date_of_birth=parse_date_flexible(student_data.get("Date of Birth") or student_data.get("dob")),
                    ai_rank=safe_int(sanitize_rank_value(student_data.get("AI rank") or student_data.get("jeeRank"))),
                    category_rank=safe_int(sanitize_rank_value(student_data.get("Category Rank") or student_data.get("categoryRank"))),
                    father_occupation=student_data.get("Father's Occupation") or student_data.get("fatherOccupation", ""),
                    father_mobile=sanitize_phone_number(student_data.get("Father Mobile Number") or student_data.get("fatherMobile", "")),
                    mother_occupation=student_data.get("Mother's Occupation") or student_data.get("motherOccupation", ""),
                    mother_mobile=sanitize_phone_number(student_data.get("Mother Mobile Number") or student_data.get("motherMobile", "")),
                    allotted_category=student_data.get("allottedcat") or student_data.get("allottedCategory", ""),
                    allotted_gender=student_data.get("Allotted Gender") or student_data.get("allottedGender", ""),
                    year=batch_year,
                    academic_year=academic_year,
                    programme_type=programme_type,
                    reported_status="NOT_REPORTED",
                    source="excel_upload",
                )
                successful += 1
        except Exception as exc:
            failed += 1
            errors.append(f"Failed to save student {name}: {exc}")

    messages = []
    if successful:
        messages.append(f"{successful} students uploaded successfully")
    if skipped_duplicates:
        messages.append(f"{skipped_duplicates} duplicates skipped")
    if skipped_invalid:
        messages.append(f"{skipped_invalid} students with validation errors skipped")
    if failed:
        messages.append(f"{failed} uploads failed")

    return {
        "success": True,
        "data": {
            "successful_uploads": successful,
            "failed_uploads": failed,
            "skipped_duplicates": skipped_duplicates,
            "validation_errors": validation_errors,
            "skipped_invalid": skipped_invalid,
            "total_processed": successful + failed + validation_errors + skipped_invalid,
            "original_count": len(data.get("students", [])),
        },
        "summary": allocation_summary(processed, programme_type),
        "errors": errors,
        "message": ". ".join(messages) + "." if messages else "No students processed.",
    }


FIELD_MAPPING = {
    "fname": "father_name", "mname": "mother_name", "jeeAppNo": "jee_app_no",
    "phoneNumber": "phone_number", "email": "personal_email", "dob": "date_of_birth",
    "aadharNumber": "aadhar_number", "jeeRank": "ai_rank", "categoryRank": "category_rank",
    "allottedGender": "allotted_gender", "allottedCategory": "allotted_category",
    "fatherOccupation": "father_occupation", "fatherMobile": "father_mobile",
    "motherOccupation": "mother_occupation", "motherMobile": "mother_mobile",
    "parentEmail": "parent_email", "bloodGroup": "blood_group",
    "bloodGroupRemarks": "blood_group_remarks", "pwdCategory": "pwd_category",
    "pwdCategoryRemarks": "pwd_category_remarks", "admissionMode": "admission_mode",
    "admissionModeRemarks": "admission_mode_remarks", "incomeGroup": "income_group",
}


def add_student(raw):
    data = dict(raw)
    programme_type = data.get("programme_type", "ug")
    batch_year, academic_year = resolve_year(data.get("academic_year"))
    require_curriculum("adding student")
    require_batches(batch_year, academic_year, "adding student")

    mapped = {}
    for key, value in data.items():
        mapped[FIELD_MAPPING.get(key, key)] = value
        if key in ("rollNumber", "instituteEmail"):
            mapped[key] = value
    data = mapped

    required = ["name", "father_name", "mother_name", "branch", "gender", "category", "pwd", "address"]
    missing = [field for field in required if not data.get(field)]
    if missing:
        raise ServiceError({"success": False, "message": f'Missing required fields: {", ".join(missing)}'})

    jee_app_no = data.get("jee_app_no")
    if jee_app_no:
        existing = StudentBatchUpload.objects.filter(jee_app_no=jee_app_no).first()
        if existing:
            raise ServiceError({"success": False, "message": f"Student with JEE Application Number {jee_app_no} already exists (Roll Number: {existing.roll_number})"})

    processed = allocate([data], programme_type, batch_year)
    if not processed:
        raise ServiceError({"success": False, "message": "Failed to process student data"})
    student_data = processed[0]

    with transaction.atomic():
        student = StudentBatchUpload.objects.create(
            name=student_data.get("name"),
            jee_app_no=student_data.get("jee_app_no") or None,
            roll_number=student_data.get("roll_number") or None,
            institute_email=student_data.get("institute_email", ""),
            father_name=student_data.get("father_name"),
            mother_name=student_data.get("mother_name"),
            gender=student_data.get("gender"),
            category=student_data.get("category"),
            pwd=student_data.get("pwd"),
            minority=data.get("minority", ""),
            date_of_birth=parse_date_flexible(data.get("date_of_birth")),
            phone_number=sanitize_phone_number(data.get("phone_number", "")),
            personal_email=data.get("personal_email", "") or data.get("alternateEmail", ""),
            parent_email=data.get("parent_email", ""),
            address=student_data.get("address"),
            state=data.get("state", ""),
            country=data.get("country", "India"),
            nationality=data.get("nationality", "Indian"),
            blood_group=data.get("blood_group", ""),
            blood_group_remarks=data.get("blood_group_remarks", ""),
            pwd_category=data.get("pwd_category", ""),
            pwd_category_remarks=data.get("pwd_category_remarks", ""),
            admission_mode=data.get("admission_mode", ""),
            admission_mode_remarks=data.get("admission_mode_remarks", ""),
            income_group=data.get("income_group", ""),
            income=data.get("income") or None,
            father_occupation=data.get("father_occupation", ""),
            father_mobile=sanitize_phone_number(data.get("father_mobile", "")),
            mother_occupation=data.get("mother_occupation", ""),
            mother_mobile=sanitize_phone_number(data.get("mother_mobile", "")),
            branch=student_data.get("branch"),
            specialization=data.get("specialization", ""),
            ai_rank=safe_int(sanitize_rank_value(data.get("ai_rank"))),
            category_rank=safe_int(sanitize_rank_value(data.get("category_rank"))),
            allotted_category=data.get("allotted_category", ""),
            allotted_gender=data.get("allotted_gender", ""),
            year=batch_year,
            academic_year=academic_year,
            programme_type=programme_type,
            reported_status="NOT_REPORTED",
            allocation_status="ALLOCATED",
            source="manual_entry",
        )

    return {
        "success": True,
        "data": {
            "student_id": student.id,
            "roll_number": student.roll_number,
            "institute_email": student.institute_email,
            "name": student.name,
        },
        "message": f"Student {student.name} added successfully.",
    }
