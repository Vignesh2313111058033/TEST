import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create the initial administrator from environment variables."

    def handle(self, *args, **options):
        username = os.getenv("DJANGO_SUPERUSER_USERNAME")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "")

        if not username or not password:
            self.stdout.write(
                "Admin bootstrap skipped: superuser environment variables are not set."
            )
            return

        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(
            **{user_model.USERNAME_FIELD: username},
            defaults={"email": email},
        )

        if created:
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created administrator '{username}'."))
            return

        self.stdout.write(
            f"Administrator '{username}' already exists; password was not changed."
        )

