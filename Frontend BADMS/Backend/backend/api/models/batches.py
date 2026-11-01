import datetime

from django.db import models

from .erp import AuthUser


def get_current_academic_year():
    today = datetime.date.today()
    return today.year if today.month >= 7 else today.year - 1


class BatchConfiguration(models.Model):
    PROGRAMME_CHOICES = [
        ("B.Tech", "Bachelor of Technology"),
        ("B.Des", "Bachelor of Design"),
        ("M.Tech", "Master of Technology"),
        ("M.Des", "Master of Design"),
        ("PhD", "Doctor of Philosophy"),
    ]
    DISCIPLINE_CHOICES = [
        ("Computer Science and Engineering", "Computer Science and Engineering"),
        ("Electronics and Communication Engineering", "Electronics and Communication Engineering"),
        ("Mechanical Engineering", "Mechanical Engineering"),
        ("Smart Manufacturing", "Smart Manufacturing"),
        ("Design", "Design"),
    ]

    programme = models.CharField(max_length=50, choices=PROGRAMME_CHOICES)
    discipline = models.CharField(max_length=100, choices=DISCIPLINE_CHOICES)
    year = models.IntegerField()
    total_seats = models.IntegerField(default=60)
    filled_seats = models.IntegerField(default=0)
    available_seats = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "programme_curriculum_batchconfiguration"
        unique_together = ("programme", "discipline", "year")
        ordering = ["programme", "discipline", "year"]

    def __str__(self):
        return f"{self.programme} - {self.discipline} ({self.year})"


class StudentBatchUpload(models.Model):
    GENDER_CHOICES = [("Male", "Male"), ("Female", "Female"), ("Other", "Other")]
    CATEGORY_CHOICES = [
        ("GEN", "General"),
        ("OBC", "Other Backward Class"),
        ("SC", "Scheduled Caste"),
        ("ST", "Scheduled Tribe"),
        ("EWS", "Economically Weaker Section"),
    ]
    PWD_CHOICES = [("YES", "Yes"), ("NO", "No")]
    PWD_CATEGORY_CHOICES = [
        ("Locomotor Disability", "Locomotor Disability"),
        ("Visual Impairment", "Visual Impairment"),
        ("Hearing Impairment", "Hearing Impairment"),
        ("Speech and Language Disability", "Speech and Language Disability"),
        ("Intellectual Disability", "Intellectual Disability"),
        ("Autism Spectrum Disorder", "Autism Spectrum Disorder"),
        ("Multiple Disabilities", "Multiple Disabilities"),
        ("Any other (remarks)", "Any other (remarks)"),
    ]
    BLOOD_GROUP_CHOICES = [
        ("A+", "A+"), ("A-", "A-"), ("B+", "B+"), ("B-", "B-"),
        ("AB+", "AB+"), ("AB-", "AB-"), ("O+", "O+"), ("O-", "O-"), ("Other", "Other"),
    ]
    ADMISSION_MODE_CHOICES = [
        ("JEE Main", "JEE Main"),
        ("JEE Advanced", "JEE Advanced"),
        ("GATE", "GATE"),
        ("DASA", "DASA"),
        ("Foreign National", "Foreign National"),
        ("Sponsored", "Sponsored"),
        ("Any other (remarks)", "Any other (remarks)"),
    ]
    INCOME_GROUP_CHOICES = [
        ("Below 1 Lakh", "Below 1 Lakh"),
        ("1-2.5 Lakhs", "1-2.5 Lakhs"),
        ("2.5-5 Lakhs", "2.5-5 Lakhs"),
        ("5-8 Lakhs", "5-8 Lakhs"),
        ("Above 8 Lakhs", "Above 8 Lakhs"),
    ]
    REPORTED_STATUS_CHOICES = [
        ("NOT_REPORTED", "Not Reported"),
        ("REPORTED", "Reported"),
        ("WITHDRAWAL", "Withdrawal"),
    ]
    PROGRAMME_TYPE_CHOICES = [("ug", "Undergraduate"), ("pg", "Postgraduate"), ("phd", "PhD")]

    jee_app_no = models.CharField(max_length=50, unique=True, blank=True, null=True)
    roll_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    institute_email = models.EmailField(blank=True, null=True)

    name = models.CharField(max_length=200)
    father_name = models.CharField(max_length=200)
    mother_name = models.CharField(max_length=200)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    pwd = models.CharField(max_length=3, choices=PWD_CHOICES, default="NO")
    minority = models.TextField(blank=True, null=True)
    blood_group = models.CharField(max_length=10, choices=BLOOD_GROUP_CHOICES, blank=True, null=True)
    blood_group_remarks = models.TextField(blank=True, null=True)
    pwd_category = models.CharField(max_length=100, choices=PWD_CATEGORY_CHOICES, blank=True, null=True)
    pwd_category_remarks = models.TextField(blank=True, null=True)

    phone_number = models.CharField(max_length=15, blank=True, null=True)
    personal_email = models.EmailField(blank=True, null=True)
    address = models.TextField()
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True, default="India")
    nationality = models.CharField(max_length=100, blank=True, null=True, default="Indian")

    branch = models.CharField(max_length=200)
    specialization = models.CharField(max_length=200, blank=True, null=True)
    section = models.CharField(max_length=2, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    ai_rank = models.IntegerField(blank=True, null=True, db_column="jee_rank")
    category_rank = models.IntegerField(blank=True, null=True)
    income_group = models.CharField(max_length=30, choices=INCOME_GROUP_CHOICES, blank=True, null=True)
    income = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    tenth_marks = models.FloatField(blank=True, null=True)
    twelfth_marks = models.FloatField(blank=True, null=True)

    father_occupation = models.CharField(max_length=200, blank=True, null=True)
    father_mobile = models.CharField(max_length=15, blank=True, null=True)
    mother_occupation = models.CharField(max_length=200, blank=True, null=True)
    mother_mobile = models.CharField(max_length=15, blank=True, null=True)
    parent_email = models.EmailField(blank=True, null=True)
    aadhar_number = models.CharField(max_length=12, blank=True, null=True)

    allotted_category = models.CharField(max_length=50, blank=True, null=True)
    allotted_gender = models.CharField(max_length=50, blank=True, null=True)
    admission_mode = models.CharField(max_length=50, choices=ADMISSION_MODE_CHOICES, blank=True, null=True)
    admission_mode_remarks = models.TextField(blank=True, null=True)

    year = models.IntegerField(db_column="batch_year", default=get_current_academic_year)
    academic_year = models.CharField(max_length=20, blank=True)
    programme_type = models.CharField(max_length=10, choices=PROGRAMME_TYPE_CHOICES)
    allocation_status = models.CharField(max_length=50, default="ALLOCATED")
    reported_status = models.CharField(max_length=20, choices=REPORTED_STATUS_CHOICES, default="NOT_REPORTED")
    source = models.CharField(max_length=50, default="admin_upload")

    user = models.ForeignKey(
        AuthUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="student_profile", db_column="user_account_id",
    )
    email_password = models.CharField(max_length=50, blank=True, null=True)
    password_email_sent = models.BooleanField(default=False)
    password_generated_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    uploaded_by = models.ForeignKey(
        AuthUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="uploaded_students", db_column="created_by_id",
    )

    #: Projected to placement, so a student keeps one resume, not one per service.
    resume_link = models.CharField(max_length=500, blank=True)
    profile_completed = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = "programme_curriculum_studentbatchupload"
        ordering = ["roll_number", "name"]

    def __str__(self):
        return f"{self.name} ({self.roll_number or self.jee_app_no})"

    def get_programme_name(self):
        if self.programme_type == "ug":
            return "B.Des" if "design" in self.branch.lower() else "B.Tech"
        if self.programme_type == "pg":
            return "M.Des" if "design" in self.branch.lower() else "M.Tech"
        if self.programme_type == "phd":
            return "PhD"
        return "Unknown"

    def get_display_branch(self):
        b = self.branch.lower()
        if "computer" in b or "cse" in b:
            return "CSE"
        if "electronics" in b or "ece" in b:
            return "ECE"
        if "mechanical" in b or "me" in b:
            return "ME"
        if "smart" in b or "manufacturing" in b:
            return "SM"
        if "design" in b:
            return "DES"
        return self.branch

    @property
    def first_name(self):
        return self.name.split()[0] if self.name else ""

    @property
    def last_name(self):
        parts = self.name.split() if self.name else []
        return " ".join(parts[1:]) if len(parts) > 1 else ""

    def _clean_branch_name(self, branch_text):
        import re
        return re.sub(r"\s*\([^)]*\)", "", branch_text).strip() if branch_text else branch_text

    def save(self, *args, **kwargs):
        if not self.academic_year:
            year = self.year or get_current_academic_year()
            self.academic_year = f"{year}-{(year + 1) % 100:02d}"
        if self.roll_number and not self.institute_email:
            self.institute_email = f"{self.roll_number.lower()}@iiitdmj.ac.in"
        for attr in ("institute_email", "personal_email", "parent_email"):
            value = getattr(self, attr)
            if value:
                setattr(self, attr, value.lower())
        if self.branch:
            self.branch = self._clean_branch_name(self.branch)
        super().save(*args, **kwargs)


class StudentStatusLog(models.Model):
    student = models.ForeignKey(StudentBatchUpload, on_delete=models.CASCADE, related_name="status_logs")
    changed_by = models.ForeignKey(AuthUser, on_delete=models.SET_NULL, null=True, blank=True)
    old_reported_status = models.CharField(max_length=20)
    new_reported_status = models.CharField(max_length=20)
    change_reason = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "programme_curriculum_studentstatuslog"
        ordering = ["-created_at"]


class UploadHistory(models.Model):
    UPLOAD_TYPE_CHOICES = [("excel", "Excel Upload"), ("manual", "Manual Entry"), ("bulk", "Bulk Import")]

    upload_type = models.CharField(max_length=20, choices=UPLOAD_TYPE_CHOICES)
    programme_type = models.CharField(max_length=10, choices=StudentBatchUpload.PROGRAMME_TYPE_CHOICES)
    total_records = models.IntegerField(default=0)
    successful_records = models.IntegerField(default=0)
    failed_records = models.IntegerField(default=0)
    file_name = models.CharField(max_length=255, blank=True, null=True)
    uploaded_by = models.ForeignKey(AuthUser, on_delete=models.SET_NULL, null=True, blank=True)
    upload_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "programme_curriculum_uploadhistory"
        ordering = ["-created_at"]
