from django.contrib import admin

from .models import ActivationHistory, AuditLog, License


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = (
        "license_key",
        "license_type",
        "is_active",
        "is_blocked",
        "violation_count",
        "created_at",
        "expiry_date",
    )
    list_filter = ("license_type", "is_active", "is_blocked")
    search_fields = ("license_key", "hardware_id")
    readonly_fields = ("license_key", "created_at", "violation_count")


@admin.register(ActivationHistory)
class ActivationHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "license_key",
        "requested_hardware_id",
        "request_ip",
        "status",
        "request_time",
    )
    list_filter = ("status", "request_time")
    search_fields = (
        "license_key",
        "requested_hardware_id",
        "registered_hardware_id",
    )
    readonly_fields = tuple(field.name for field in ActivationHistory._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "actor", "license", "request_ip", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("action", "license__license_key", "actor__username")
    readonly_fields = tuple(field.name for field in AuditLog._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
