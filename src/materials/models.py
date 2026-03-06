from django.conf import settings
from django.db import models

from courses.models import Course


UserModel = settings.AUTH_USER_MODEL


class Material(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="materials",
    )

    creator = models.ForeignKey(
        UserModel,
        on_delete=models.CASCADE,
        related_name="created_materials",
    )

    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.course.title})"


class MaterialFile(models.Model):
    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name="files",
    )

    file = models.FileField(upload_to="materials/")

    uploaded_at = models.DateTimeField(auto_now_add=True)

    @property
    def filename(self):
        return self.file.name.split("/")[-1]

    def __str__(self):
        return f"{self.filename} for {self.material.title}"
