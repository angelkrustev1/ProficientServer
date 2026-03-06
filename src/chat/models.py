from django.conf import settings
from django.db import models

from courses.models import Course


UserModel = settings.AUTH_USER_MODEL


class Message(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    author = models.ForeignKey(
        UserModel,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )

    content = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    @property
    def likes_count(self):
        return self.likes.count()

    def __str__(self):
        return f"{self.author} in {self.course.title}: {self.content[:30]}"


class MessageLike(models.Model):
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="likes",
    )

    user = models.ForeignKey(
        UserModel,
        on_delete=models.CASCADE,
        related_name="message_likes",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["message", "user"],
                name="unique_like_per_user_per_message",
            )
        ]

    def __str__(self):
        return f"{self.user} liked message {self.message.id}"
