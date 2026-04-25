import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or update a superuser from environment variables."

    def handle(self, *args, **options):
        email = os.getenv("DJANGO_SUPERUSER_EMAIL")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")

        if not email or not password:
            self.stdout.write(self.style.WARNING(
                "DJANGO_SUPERUSER_EMAIL or DJANGO_SUPERUSER_PASSWORD is missing. Skipping superuser creation."
            ))
            return

        User = get_user_model()
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )

        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Superuser created: {email}"))
            return

        updated = False

        if not user.is_staff:
            user.is_staff = True
            updated = True

        if not user.is_superuser:
            user.is_superuser = True
            updated = True

        if not user.is_active:
            user.is_active = True
            updated = True

        if not user.check_password(password):
            user.set_password(password)
            updated = True

        if updated:
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Superuser updated: {email}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Superuser already exists: {email}"))
