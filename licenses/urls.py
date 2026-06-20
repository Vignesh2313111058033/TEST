from django.urls import path

from .views import (
    ActivationHistoryListView,
    AuditLogListView,
    LicenseDetailView,
    LicenseListCreateView,
    LicenseStateView,
    PublicLicenseActivationView,
    SuspiciousAttemptListView,
)


urlpatterns = [
    path("activate/", PublicLicenseActivationView.as_view(), name="license-activation"),
    path("admin/licenses/", LicenseListCreateView.as_view(), name="license-list-create"),
    path(
        "admin/licenses/<str:license_key>/",
        LicenseDetailView.as_view(),
        name="license-detail",
    ),
    path(
        "admin/licenses/<str:license_key>/<str:action>/",
        LicenseStateView.as_view(),
        name="license-state",
    ),
    path(
        "admin/activation-history/",
        ActivationHistoryListView.as_view(),
        name="activation-history",
    ),
    path(
        "admin/suspicious-attempts/",
        SuspiciousAttemptListView.as_view(),
        name="suspicious-attempts",
    ),
    path("admin/audit-logs/", AuditLogListView.as_view(), name="audit-logs"),
]

