import datetime

from django.db import models


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.BooleanField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.BooleanField()
    is_active = models.BooleanField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "auth_user"


class Programme(models.Model):
    category = models.CharField(max_length=3, null=False, blank=False)
    name = models.CharField(max_length=70, null=False, unique=True, blank=False)
    programme_begin_year = models.PositiveIntegerField(
        default=datetime.date.today().year, null=False
    )

    class Meta:
        managed = False
        db_table = "programme_curriculum_programme"

    def __str__(self):
        return str(self.category + " - " + self.name)


class Discipline(models.Model):
    name = models.CharField(max_length=100, null=False, unique=True, blank=False)
    acronym = models.CharField(max_length=10, null=False, default="", blank=False)
    programmes = models.ManyToManyField(Programme, blank=True)

    class Meta:
        managed = False
        db_table = "programme_curriculum_discipline"

    def __str__(self):
        return str(self.name) + " " + str(self.acronym)


class Curriculum(models.Model):
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, null=False)
    name = models.CharField(max_length=100, null=False, blank=False)
    version = models.DecimalField(default=1.0, max_digits=5, decimal_places=1)
    working_curriculum = models.BooleanField(default=True, null=False)
    no_of_semester = models.PositiveIntegerField(default=1, null=False)
    min_credit = models.PositiveIntegerField(default=0, null=False)
    latest_version = models.BooleanField(default=True)

    class Meta:
        unique_together = (
            "name",
            "version",
        )
        managed = False
        db_table = "programme_curriculum_curriculum"

    def __str__(self):
        return str(self.name + " v" + str(self.version))


class Batch(models.Model):
    name = models.CharField(max_length=50, null=False, blank=False)
    discipline = models.ForeignKey(Discipline, null=False, on_delete=models.CASCADE)
    year = models.PositiveIntegerField(default=datetime.date.today().year, null=False)
    curriculum = models.ForeignKey(
        Curriculum, null=True, blank=True, on_delete=models.SET_NULL
    )
    running_batch = models.BooleanField(default=True)
    total_seats = models.IntegerField(default=0)
    curriculum_options = models.JSONField(null=True, blank=True)

    class Meta:
        unique_together = (
            "name",
            "discipline",
            "year",
        )
        managed = False
        db_table = "programme_curriculum_batch"

    def __str__(self):
        return (
            str(self.name) + " " + str(self.discipline.acronym) + " " + str(self.year)
        )


class GlobalsDepartmentinfo(models.Model):
    name = models.CharField(unique=True, max_length=100)

    class Meta:
        managed = False
        db_table = "globals_departmentinfo"


class GlobalsDesignation(models.Model):
    name = models.CharField(unique=True, max_length=50)
    full_name = models.CharField(max_length=100)
    type = models.CharField(max_length=30)
    basic = models.BooleanField(default=False, null=False, blank=False)
    category = models.CharField(max_length=20, null=True, blank=True)
    dept_if_not_basic = models.ForeignKey(
        GlobalsDepartmentinfo, on_delete=models.CASCADE, blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "globals_designation"


class GlobalsExtrainfo(models.Model):
    id = models.CharField(primary_key=True, max_length=50)
    title = models.CharField(max_length=20)
    sex = models.CharField(max_length=2)
    date_of_birth = models.DateField()
    user_status = models.CharField(max_length=50)
    address = models.TextField()
    phone_no = models.BigIntegerField(blank=True, null=True)
    user_type = models.CharField(max_length=20)
    profile_picture = models.CharField(max_length=100, blank=True, null=True)
    about_me = models.TextField()
    date_modified = models.DateTimeField(blank=True, null=True)
    department = models.ForeignKey(
        GlobalsDepartmentinfo, on_delete=models.CASCADE, blank=True, null=True
    )
    user = models.OneToOneField(AuthUser, on_delete=models.CASCADE)

    class Meta:
        managed = False
        db_table = "globals_extrainfo"


class Staff(models.Model):
    id = models.OneToOneField(
        GlobalsExtrainfo, on_delete=models.CASCADE, primary_key=True
    )

    def __str__(self):
        return str(self.id)

    class Meta:
        managed = False
        db_table = "globals_staff"


class GlobalsHoldsdesignation(models.Model):
    held_at = models.DateTimeField(auto_now=True)
    designation = models.ForeignKey(
        GlobalsDesignation, related_name="designees", on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        AuthUser, related_name="holds_designations", on_delete=models.CASCADE
    )
    working = models.ForeignKey(
        AuthUser, related_name="current_designation", on_delete=models.CASCADE
    )

    class Meta:
        managed = False
        db_table = "globals_holdsdesignation"
        unique_together = (
            ("user", "designation"),
            ("working", "designation"),
        )


class GlobalsModuleaccess(models.Model):
    designation = models.CharField(max_length=155)
    program_and_curriculum = models.BooleanField()
    course_registration = models.BooleanField()
    # Both NOT NULL on the real table; missing here meant a new designation
    # could not be created at all, since the shadow model had no field to set.
    thesis_research = models.BooleanField()
    course_management = models.BooleanField()
    other_academics = models.BooleanField()
    spacs = models.BooleanField()
    department = models.BooleanField()
    database = models.BooleanField()
    examinations = models.BooleanField()
    hr = models.BooleanField()
    iwd = models.BooleanField()
    complaint_management = models.BooleanField()
    fts = models.BooleanField()
    purchase_and_store = models.BooleanField()
    rspc = models.BooleanField()
    hostel_management = models.BooleanField()
    mess_management = models.BooleanField()
    gymkhana = models.BooleanField()
    placement_cell = models.BooleanField()
    visitor_hostel = models.BooleanField()
    phc = models.BooleanField()
    inventory_management = models.BooleanField()

    class Meta:
        managed = False
        db_table = "globals_moduleaccess"


class Student(models.Model):
    id = models.OneToOneField(
        GlobalsExtrainfo, on_delete=models.CASCADE, primary_key=True
    )
    programme = models.CharField(max_length=10)
    batch = models.IntegerField(default=2016)
    batch_id = models.ForeignKey(Batch, null=True, blank=True, on_delete=models.CASCADE)
    cpi = models.FloatField(default=0)
    category = models.CharField(max_length=10, null=False)
    father_name = models.CharField(max_length=40, default="", null=True)
    mother_name = models.CharField(max_length=40, default="", null=True)
    hall_no = models.IntegerField(default=0)
    room_no = models.CharField(max_length=10, blank=True, null=True)
    specialization = models.CharField(max_length=40, null=True, default="")
    curr_semester_no = models.IntegerField(default=1)

    class Meta:
        managed = False
        db_table = "academic_information_student"

    def __str__(self):
        username = str(self.id.user.username)
        return username


class GlobalsFaculty(models.Model):
    id = models.OneToOneField(
        GlobalsExtrainfo, on_delete=models.CASCADE, primary_key=True
    )

    def __str__(self):
        return str(self.id)

    class Meta:
        managed = False
        db_table = "globals_faculty"


# ---------------------------------------------------------------------------
# Grades and result declarations.
#
# Read only by iam/erp_source.py, to project each student's declared CPI into
# system_db. Placement eligibility needs a CGPA (PC-BR-004) and
# academic_information_student.cpi is permanently 0.0 — its only writers set
# zero at creation — so the number has to be computed from the grade rows the
# way the ERP itself computes it.
# ---------------------------------------------------------------------------
class Course(models.Model):
    """programme_curriculum.Course. Only the two fields the grade math uses."""

    code = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    credit = models.PositiveIntegerField(default=0, null=True)

    class Meta:
        managed = False
        db_table = "programme_curriculum_course"

    def __str__(self):
        return f"{self.code} ({self.credit})"


class StudentGrade(models.Model):
    """online_cms.Student_grades — one row per course per student per attempt.

    `roll_no` is a TEXT column holding globals_extrainfo.id (the roll number),
    NOT auth_user.id. That mismatch is the reason this module exists: joining
    grades to a platform user_id takes two hops.
    """

    course_id = models.ForeignKey(Course, on_delete=models.DO_NOTHING,
                                  db_column="course_id_id")
    semester = models.IntegerField(default=1)
    year = models.IntegerField(default=2016)
    roll_no = models.TextField()
    grade = models.TextField()
    batch = models.IntegerField(default=2021)
    academic_year = models.CharField(max_length=9, null=True)
    semester_type = models.CharField(max_length=20, null=True)

    class Meta:
        managed = False
        db_table = "online_cms_student_grades"


class CourseRegistration(models.Model):
    course_id = models.ForeignKey(Course, on_delete=models.DO_NOTHING,
                                  db_column="course_id_id")
    student_id = models.ForeignKey(Student, on_delete=models.DO_NOTHING,
                                   db_column="student_id_id")
    semester_type = models.CharField(max_length=20, null=True)
    working_year = models.IntegerField(null=True)

    class Meta:
        managed = False
        db_table = "course_registration"


class CourseReplacement(models.Model):
    """A swayam/replacement course supersedes the elective it replaced.

    Both sides point at course_registration, so resolving it to course codes
    needs the join above.
    """

    old_course_registration = models.ForeignKey(
        CourseRegistration, on_delete=models.DO_NOTHING,
        db_column="old_course_registration_id", related_name="+")
    new_course_registration = models.ForeignKey(
        CourseRegistration, on_delete=models.DO_NOTHING,
        db_column="new_course_registration_id", related_name="+")

    class Meta:
        managed = False
        db_table = "course_replacement"


class ResultAnnouncement(models.Model):
    """When a batch's semester result was declared.

    `announced` is the gate. Note there is no `declared_at` column — created_at
    is when the admin created the not-yet-announced placeholder, so it is a
    lower bound on declaration time, not the declaration time itself.
    """

    batch = models.ForeignKey(Batch, on_delete=models.DO_NOTHING,
                              db_column="batch_id")
    semester = models.PositiveIntegerField()
    semester_type = models.CharField(max_length=20, null=True)
    announced = models.BooleanField(default=False)
    per_student_selection = models.BooleanField(default=False)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "examination_resultannouncement"


class PublishedResultStudent(models.Model):
    """The per-student allow-list for an announcement.

    When `per_student_selection` is true, only students listed here may see
    their result — and therefore only they have a declared CPI.
    """

    announcement = models.ForeignKey(ResultAnnouncement, on_delete=models.DO_NOTHING,
                                     db_column="announcement_id",
                                     related_name="published_students")
    roll_no = models.CharField(max_length=20)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "examination_publishedresultstudent"


class PhdStudentBatchUpload(models.Model):
    """The same record for doctoral admissions, in its own table."""

    roll_number = models.CharField(max_length=20)
    user_account_id = models.IntegerField(null=True)
    resume_link = models.CharField(max_length=500, blank=True)
    profile_completed = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = "programme_curriculum_phdstudentbatchupload"
