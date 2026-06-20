from django.db.models import F
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import ActivationHistory, AuditLog, License
from .permissions import IsAdminUser
from .serializers import (
    ActivationHistorySerializer,
    AdminTokenObtainPairSerializer,
    AuditLogSerializer,
    LicenseActivationSerializer,
    LicenseSerializer,
)
from .services import activate_license, write_audit_log
from .throttles import ActivationRateThrottle, LoginRateThrottle


class AdminTokenObtainPairView(TokenObtainPairView):
    serializer_class = AdminTokenObtainPairSerializer
    throttle_classes = (LoginRateThrottle,)


class LicenseListCreateView(generics.ListCreateAPIView):
    permission_classes = (IsAdminUser,)
    serializer_class = LicenseSerializer

    def get_queryset(self):
        queryset = License.objects.all()
        for field in ("license_type", "is_active", "is_blocked"):
            value = self.request.query_params.get(field)
            if value is not None:
                if field in {"is_active", "is_blocked"}:
                    value = value.lower() in {"1", "true", "yes"}
                queryset = queryset.filter(**{field: value})
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(license_key__icontains=search)
        return queryset

    def perform_create(self, serializer):
        license_obj = serializer.save()
        write_audit_log(
            action="LICENSE_CREATED",
            request=self.request,
            license_obj=license_obj,
            metadata={"license_type": license_obj.license_type},
        )


class LicenseDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = (IsAdminUser,)
    serializer_class = LicenseSerializer
    queryset = License.objects.all()
    lookup_field = "license_key"

    def perform_update(self, serializer):
        before = {
            "license_type": serializer.instance.license_type,
            "expiry_date": str(serializer.instance.expiry_date),
            "is_active": serializer.instance.is_active,
        }
        license_obj = serializer.save()
        write_audit_log(
            action="LICENSE_UPDATED",
            request=self.request,
            license_obj=license_obj,
            metadata={"before": before},
        )


class LicenseStateView(APIView):
    permission_classes = (IsAdminUser,)
    actions = {
        "activate": ("is_active", True, "LICENSE_ACTIVATED"),
        "deactivate": ("is_active", False, "LICENSE_DEACTIVATED"),
        "block": ("is_blocked", True, "LICENSE_BLOCKED"),
        "unblock": ("is_blocked", False, "LICENSE_UNBLOCKED"),
    }

    def post(self, request, license_key, action):
        try:
            field, value, audit_action = self.actions[action]
            license_obj = License.objects.get(license_key=license_key)
        except KeyError:
            return Response({"detail": "Unknown action."}, status=status.HTTP_404_NOT_FOUND)
        except License.DoesNotExist:
            return Response({"detail": "License not found."}, status=status.HTTP_404_NOT_FOUND)

        setattr(license_obj, field, value)
        license_obj.save(update_fields=(field,))
        write_audit_log(
            action=audit_action,
            request=request,
            license_obj=license_obj,
        )
        return Response(LicenseSerializer(license_obj).data)


class PublicLicenseActivationView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (ActivationRateThrottle,)

    def post(self, request):
        serializer = LicenseActivationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        license_obj, activation_status, message = activate_license(
            request=request,
            **serializer.validated_data,
        )
        payload = {
            "status": activation_status,
            "message": message,
            "license": LicenseSerializer(license_obj).data if license_obj else None,
        }
        if activation_status == ActivationHistory.Status.SUCCESS:
            return Response(payload, status=status.HTTP_200_OK)
        if activation_status == ActivationHistory.Status.BLOCKED:
            return Response(payload, status=status.HTTP_403_FORBIDDEN)
        return Response(payload, status=status.HTTP_400_BAD_REQUEST)


class ActivationHistoryListView(generics.ListAPIView):
    permission_classes = (IsAdminUser,)
    serializer_class = ActivationHistorySerializer

    def get_queryset(self):
        queryset = ActivationHistory.objects.all()
        license_key = self.request.query_params.get("license_key")
        history_status = self.request.query_params.get("status")
        if license_key:
            queryset = queryset.filter(license_key=license_key.upper())
        if history_status:
            queryset = queryset.filter(status=history_status.upper())
        return queryset


class SuspiciousAttemptListView(generics.ListAPIView):
    permission_classes = (IsAdminUser,)
    serializer_class = ActivationHistorySerializer

    def get_queryset(self):
        return (
            ActivationHistory.objects.exclude(status=ActivationHistory.Status.SUCCESS)
            .exclude(registered_hardware_id__isnull=True)
            .exclude(requested_hardware_id=F("registered_hardware_id"))
        )


class AuditLogListView(generics.ListAPIView):
    permission_classes = (IsAdminUser,)
    serializer_class = AuditLogSerializer
    queryset = AuditLog.objects.select_related("actor", "license").all()

