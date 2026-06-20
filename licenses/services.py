import logging

from django.db import transaction
from django.db.models import F

from .models import ActivationHistory, AuditLog, License
from .utils import get_client_ip


audit_logger = logging.getLogger("licenses.audit")


def write_audit_log(*, action, request, license_obj=None, metadata=None):
    actor = request.user if getattr(request.user, "is_authenticated", False) else None
    log = AuditLog.objects.create(
        actor=actor,
        action=action,
        license=license_obj,
        request_ip=get_client_ip(request),
        metadata=metadata or {},
    )
    audit_logger.info(
        "action=%s actor=%s license=%s ip=%s",
        action,
        getattr(actor, "pk", None),
        getattr(license_obj, "license_key", None),
        log.request_ip,
    )
    return log


def _history(*, license_obj, license_key, hardware_id, ip, status, reason):
    return ActivationHistory.objects.create(
        license=license_obj,
        license_key=license_key,
        requested_hardware_id=hardware_id,
        registered_hardware_id=(
            license_obj.hardware_id if license_obj else None
        ),
        request_ip=ip,
        status=status,
        reason=reason,
    )


@transaction.atomic
def activate_license(*, license_key, hardware_id, request):
    ip = get_client_ip(request)
    try:
        license_obj = License.objects.select_for_update().get(license_key=license_key)
    except License.DoesNotExist:
        _history(
            license_obj=None,
            license_key=license_key,
            hardware_id=hardware_id,
            ip=ip,
            status=ActivationHistory.Status.REJECTED,
            reason="License does not exist.",
        )
        return None, ActivationHistory.Status.REJECTED, "License does not exist."

    if license_obj.is_blocked:
        _history(
            license_obj=license_obj,
            license_key=license_key,
            hardware_id=hardware_id,
            ip=ip,
            status=ActivationHistory.Status.BLOCKED,
            reason="License is blocked.",
        )
        return license_obj, ActivationHistory.Status.BLOCKED, "License is blocked."

    if not license_obj.is_active:
        _history(
            license_obj=license_obj,
            license_key=license_key,
            hardware_id=hardware_id,
            ip=ip,
            status=ActivationHistory.Status.REJECTED,
            reason="License is inactive.",
        )
        return license_obj, ActivationHistory.Status.REJECTED, "License is inactive."

    if license_obj.is_expired:
        _history(
            license_obj=license_obj,
            license_key=license_key,
            hardware_id=hardware_id,
            ip=ip,
            status=ActivationHistory.Status.REJECTED,
            reason="License has expired.",
        )
        return license_obj, ActivationHistory.Status.REJECTED, "License has expired."

    if not license_obj.hardware_id:
        license_obj.hardware_id = hardware_id
        license_obj.save(update_fields=("hardware_id",))
        _history(
            license_obj=license_obj,
            license_key=license_key,
            hardware_id=hardware_id,
            ip=ip,
            status=ActivationHistory.Status.SUCCESS,
            reason="First activation completed.",
        )
        return license_obj, ActivationHistory.Status.SUCCESS, "License activated."

    if license_obj.hardware_id == hardware_id:
        _history(
            license_obj=license_obj,
            license_key=license_key,
            hardware_id=hardware_id,
            ip=ip,
            status=ActivationHistory.Status.SUCCESS,
            reason="Hardware ID matched.",
        )
        return license_obj, ActivationHistory.Status.SUCCESS, "License is valid."

    License.objects.filter(pk=license_obj.pk).update(
        violation_count=F("violation_count") + 1
    )
    license_obj.refresh_from_db(fields=("violation_count", "is_blocked"))
    if license_obj.violation_count > 5:
        license_obj.is_blocked = True
        license_obj.save(update_fields=("is_blocked",))
        status = ActivationHistory.Status.BLOCKED
        reason = "Hardware mismatch; license automatically blocked."
    else:
        status = ActivationHistory.Status.REJECTED
        reason = "Hardware ID does not match the registered device."

    _history(
        license_obj=license_obj,
        license_key=license_key,
        hardware_id=hardware_id,
        ip=ip,
        status=status,
        reason=reason,
    )
    return license_obj, status, reason
