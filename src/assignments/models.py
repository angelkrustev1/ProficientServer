from django.conf import settings
from django.db import models
from django.utils import timezone

from courses.models import Course


UserModel = settings.AUTH_USER_MODEL


class Assignment(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="assignments",
    )

    creator = models.ForeignKey(
        UserModel,
        on_delete=models.CASCADE,
        related_name="created_assignments",
    )

    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.course.title})"


class AssignmentFile(models.Model):
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="files",
    )

    file = models.FileField(upload_to="assignments/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    @property
    def filename(self):
        return self.file.name.split("/")[-1]

    def __str__(self):
        return f"{self.filename} for {self.assignment.title}"


class Submission(models.Model):
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="submissions",
    )

    user = models.ForeignKey(
        UserModel,
        on_delete=models.CASCADE,
        related_name="assignment_submissions",
    )

    is_submitted = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "user"],
                name="unique_submission_per_user_per_assignment",
            )
        ]

    def mark_submitted(self):
        self.is_submitted = True
        self.submitted_at = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.user} -> {self.assignment.title}"


class SubmissionFile(models.Model):
    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name="files",
    )

    file = models.FileField(upload_to="submissions/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    @property
    def filename(self):
        return self.file.name.split("/")[-1]

    def __str__(self):
        return f"{self.filename} for {self.submission}"
