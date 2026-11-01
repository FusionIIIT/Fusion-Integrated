from django.db import models


class Quiz(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("scheduled", "Scheduled"),
        ("published", "Published"),
        ("closed", "Closed"),
        ("archived", "Archived"),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    course_code = models.CharField(max_length=50, blank=True)
    duration_minutes = models.PositiveIntegerField(default=30)
    max_marks = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    passing_marks = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    max_attempts = models.PositiveIntegerField(default=1)

    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft"
    )

    randomize_questions = models.BooleanField(default=False)
    randomize_options = models.BooleanField(default=False)
    allow_back_navigation = models.BooleanField(default=True)
    negative_marking = models.BooleanField(default=False)
    negative_marks_per_question = models.DecimalField(
        max_digits=6, decimal_places=2, default=0
    )
    results_released = models.BooleanField(default=False)

    created_by = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Question(models.Model):
    TYPE_CHOICES = [
        ("mcq", "Multiple Choice"),
        ("multi_select", "Multiple Select"),
        ("true_false", "True/False"),
        ("fill_in_the_blank", "Fill in the Blank"),
        ("short_answer", "Short Answer"),
    ]

    DIFFICULTY_CHOICES = [
        ("easy", "Easy"),
        ("medium", "Medium"),
        ("hard", "Hard"),
    ]

    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    text = models.TextField()
    options = models.JSONField(default=list, blank=True)
    answer = models.TextField(null=True, blank=True)
    marks = models.DecimalField(max_digits=6, decimal_places=2, default=1)
    negative_marks = models.DecimalField(
        max_digits=6, decimal_places=2, default=0
    )
    topic = models.CharField(max_length=120, blank=True)
    unit = models.CharField(max_length=120, blank=True)
    difficulty = models.CharField(
        max_length=20, choices=DIFFICULTY_CHOICES, default="medium"
    )
    image_url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)

    quiz = models.ForeignKey(
        Quiz, on_delete=models.CASCADE, related_name="questions"
    )

    def __str__(self):
        return self.text


class QuizAttempt(models.Model):
    STATUS_CHOICES = [
        ("in_progress", "In Progress"),
        ("submitted", "Submitted"),
        ("auto_submitted", "Auto Submitted"),
        ("evaluated", "Evaluated"),
    ]

    quiz = models.ForeignKey(
        Quiz, on_delete=models.CASCADE, related_name="attempts"
    )
    student_id = models.CharField(max_length=255)
    attempt_number = models.PositiveIntegerField(default=1)
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    submitted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="in_progress"
    )
    score = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    evaluated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["quiz", "student_id", "attempt_number"],
                name="unique_quiz_student_attempt",
            )
        ]

    def __str__(self):
        return f"{self.quiz.title} - {self.student_id} - Attempt {self.attempt_number}"


class QuizResponse(models.Model):
    attempt = models.ForeignKey(
        QuizAttempt, on_delete=models.CASCADE, related_name="responses"
    )
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="responses"
    )
    answer = models.JSONField(null=True, blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    marks_awarded = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    evaluated_by = models.CharField(max_length=255, blank=True)
    evaluated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "question"],
                name="unique_attempt_question_response",
            )
        ]

    def __str__(self):
        return f"Response {self.attempt_id}:{self.question_id}"
