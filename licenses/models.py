from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .utils import generate_license_key


class License(models.Model):
    class Type(models.TextChoices):
        PERMANENT = "PERMANENT", "Permanent"
        EXPIRY_BASED = "EXPIRY_BASED", "Expiry Based"

    license_key = models.CharField(
        max_length=18,
        unique=True,
        db_index=True,
        default=generate_license_key,
        editable=False,
    )
    license_type = models.CharField(max_length=20, choices=Type.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField(null=True, blank=True, db_index=True)
    hardware_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_blocked = models.BooleanField(default=False, db_index=True)
    violation_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(license_type="PERMANENT", expiry_date__isnull=True)
                    | models.Q(license_type="EXPIRY_BASED", expiry_date__isnull=False)
                ),
                name="license_type_expiry_consistency",
            )
        ]

    def clean(self):
        if self.license_type == self.Type.PERMANENT and self.expiry_date is not None:
            raise ValidationError({"expiry_date": "Permanent licenses cannot expire."})
        if self.license_type == self.Type.EXPIRY_BASED and self.expiry_date is None:
            raise ValidationError({"expiry_date": "Expiry based licenses require an expiry date."})
        if self.expiry_date and self.expiry_date <= timezone.now():
            raise ValidationError({"expiry_date": "Expiry date must be in the future."})

    def save(self, *args, **kwargs):
        if not self.license_key:
            for _ in range(10):
                candidate = generate_license_key()
                if not type(self).objects.filter(license_key=candidate).exists():
                    self.license_key = candidate
                    break
            else:
                raise RuntimeError("Unable to generate a unique license key.")
        return super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return bool(self.expiry_date and self.expiry_date <= timezone.now())

    def __str__(self):
        return self.license_key


class ActivationHistory(models.Model):
    class Status(models.TextChoices):
        SUCCESS = "SUCCESS", "Success"
        REJECTED = "REJECTED", "Rejected"
        BLOCKED = "BLOCKED", "Blocked"

    license = models.ForeignKey(
        License,
        on_delete=models.CASCADE,
        related_name="activation_history",
        null=True,
        blank=True,
    )
    license_key = models.CharField(max_length=18, db_index=True)
    requested_hardware_id = models.CharField(max_length=255)
    registered_hardware_id = models.CharField(max_length=255, null=True, blank=True)
    request_ip = models.GenericIPAddressField(null=True, blank=True)
    request_time = models.DateTimeField(auto_now_add=True, db_index=True)
    status = models.CharField(max_length=10, choices=Status.choices, db_index=True)
    reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("-request_time",)
        indexes = [
            models.Index(fields=("status", "request_time")),
            models.Index(fields=("license_key", "request_time")),
        ]

    def __str__(self):
        return f"{self.license_key} - {self.status}"


class AuditLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="license_audit_logs",
    )
    action = models.CharField(max_length=100, db_index=True)
    license = models.ForeignKey(
        License,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    request_ip = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.action
