from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models

from accounts.managers import AppUserManager


class AppUser(AbstractBaseUser, PermissionsMixin):
    class Meta:
        permissions = [
            ('can_administer_profiles', 'Can administer all profiles'),
        ]

    email = models.EmailField(unique=True)

    date_joined = models.DateTimeField(
        auto_now_add=True,
        blank=True,
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = AppUserManager()

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    profile_picture = models.URLField(blank=True)

    def __str__(self):
        return self.email

