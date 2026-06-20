import re

from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import ActivationHistory, AuditLog, License
LICENSE_KEY_PATTERN = re.compile(r"^MED-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$")


class AdminTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            username=attrs.get(self.username_field),
            password=attrs.get("password"),
        )
        if not user or not user.is_active or not user.is_staff:
            raise serializers.ValidationError("Valid administrator credentials are required.")
        data = super().validate(attrs)
        data["user"] = {"id": user.id, "username": user.get_username()}
        return data


class LicenseSerializer(serializers.ModelSerializer):
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = License
        fields = (
            "id",
            "license_key",
            "license_type",
            "created_at",
            "expiry_date",
            "hardware_id",
            "is_active",
            "is_blocked",
            "violation_count",
            "is_expired",
        )
        read_only_fields = (
            "id",
            "license_key",
            "created_at",
            "hardware_id",
            "is_blocked",
            "violation_count",
            "is_expired",
        )

    def validate(self, attrs):
        license_type = attrs.get(
            "license_type", getattr(self.instance, "license_type", None)
        )
        expiry_date = attrs.get(
            "expiry_date", getattr(self.instance, "expiry_date", None)
        )
        if license_type == License.Type.PERMANENT and expiry_date is not None:
            raise serializers.ValidationError(
                {"expiry_date": "Permanent licenses cannot have an expiry date."}
            )
        if license_type == License.Type.EXPIRY_BASED:
            if expiry_date is None:
                raise serializers.ValidationError(
                    {"expiry_date": "Expiry based licenses require an expiry date."}
                )
            if expiry_date <= timezone.now():
                raise serializers.ValidationError(
                    {"expiry_date": "Expiry date must be in the future."}
                )
        return attrs

class LicenseActivationSerializer(serializers.Serializer):
    license_key = serializers.CharField(max_length=18)
    hardware_id = serializers.CharField(max_length=255, trim_whitespace=True)

    def validate_license_key(self, value):
        value = value.strip().upper()
        if not LICENSE_KEY_PATTERN.fullmatch(value):
            raise serializers.ValidationError(
                "License key must use the format MED-XXXX-XXXX-XXXX."
            )
        return value

    def validate_hardware_id(self, value):
        if not value:
            raise serializers.ValidationError("Hardware ID cannot be empty.")
        return value


class ActivationHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivationHistory
        fields = (
            "id",
            "license_key",
            "requested_hardware_id",
            "registered_hardware_id",
            "request_ip",
            "request_time",
            "status",
            "reason",
        )


class AuditLogSerializer(serializers.ModelSerializer):
    actor = serializers.CharField(source="actor.username", allow_null=True)
    license_key = serializers.CharField(source="license.license_key", allow_null=True)

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "actor",
            "action",
            "license_key",
            "request_ip",
            "metadata",
            "created_at",
        )
