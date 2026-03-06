from django.db import models


class Exam(models.Model):
    title = models.CharField(max_length=255)
    subject = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)

    image = models.ImageField(
        upload_to="exam_images/",
        blank=True,
        null=True,
        help_text="Optional image representing the exam."
    )

    max_points = models.PositiveIntegerField(default=0)
    time_duration_minutes = models.PositiveIntegerField(
        default=30,
        help_text="Duration of the exam in minutes."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Reading(models.Model):
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="readings",
    )
    title = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title or f"Reading {self.pk}"


class Question(models.Model):
    class QuestionType(models.TextChoices):
        MULTIPLE_CHOICE = "mcq", "Multiple Choice"
        WRITTEN = "written", "Written Answer"

    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    reading = models.ForeignKey(
        Reading,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions",
    )

    question_type = models.CharField(
        max_length=20,
        choices=QuestionType.choices,
    )
    instruction = models.CharField(
        max_length=255,
        blank=True,
        help_text="Example: Choose one correct answer / Choose two correct answers.",
    )
    text = models.TextField()
    prompt_image = models.URLField(
        blank=True,
        help_text="Optional image URL for visual questions.",
    )
    correct_answer = models.TextField(
        blank=True,
        help_text="Use mainly for written questions.",
    )
    required_choices_count = models.PositiveIntegerField(
        default=1,
        help_text="How many choices the user is expected to select for MCQ questions.",
    )
    points = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=0)
    level = models.CharField(max_length=20, blank=True)
    category = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"Question {self.pk} - {self.exam.title}"


class QuestionChoice(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="choices",
    )
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.text
