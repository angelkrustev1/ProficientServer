import secrets
import string

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, IntegrityError, transaction


UserModel = settings.AUTH_USER_MODEL


def normalize_creator_code(code: str) -> str:
    # Normalize: strip spaces, uppercase
    return code.strip().upper()


class Course(models.Model):
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="course_images/", blank=True, null=True)

    creator = models.ForeignKey(
        UserModel,
        on_delete=models.CASCADE,
        related_name="created_courses",
    )

    # Creator chooses this (like "NIKI", "MATH", "BIO")
    creator_code = models.CharField(max_length=30)

    # Generated, globally unique
    join_code = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
        db_index=True,
    )

    members = models.ManyToManyField(
        UserModel,
        related_name="joined_courses",
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        self.creator_code = normalize_creator_code(self.creator_code)

        allowed = set(string.ascii_uppercase + string.digits + "_-")
        if any(ch not in allowed for ch in self.creator_code):
            raise ValidationError({
                "creator_code": "Use only A-Z, 0-9, _ or - (no spaces)."
            })

        if len(self.creator_code) < 3:
            raise ValidationError({
                "creator_code": "Must be at least 3 characters."
            })

    @staticmethod
    def _generate_suffix(length: int = 6) -> str:
        alphabet = string.ascii_uppercase + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def _build_join_code(self) -> str:
        return f"{self.creator_code}-{self._generate_suffix(6)}"

    def save(self, *args, **kwargs):
        self.full_clean()

        if self._state.adding and not self.join_code:
            for _ in range(20):
                self.join_code = self._build_join_code()
                try:
                    with transaction.atomic():
                        return super().save(*args, **kwargs)
                except IntegrityError:
                    self.join_code = ""
            raise RuntimeError("Could not generate a unique join code. Try again.")

        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.join_code})"
