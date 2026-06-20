from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from licenses.models import ActivationHistory, AuditLog, License


@override_settings(
    REST_FRAMEWORK={
        "DEFAULT_AUTHENTICATION_CLASSES": (
            "rest_framework_simplejwt.authentication.JWTAuthentication",
        ),
        "DEFAULT_THROTTLE_RATES": {
            "anon": "1000/minute",
            "user": "1000/minute",
            "activation": "1000/minute",
            "login": "1000/minute",
        },
    }
)
class LicenseApiTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username="admin",
            password="StrongPass123!",
            is_staff=True,
            is_superuser=True,
        )

    def authenticate_admin(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"username": "admin", "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def create_license(self, **overrides):
        data = {
            "license_key": "MED-AAAA-BBBB-CCCC",
            "license_type": License.Type.PERMANENT,
            "is_active": True,
        }
        data.update(overrides)
        return License.objects.create(**data)

    def test_non_admin_cannot_log_in(self):
        get_user_model().objects.create_user(username="user", password="Pass12345!")
        response = self.client.post(
            "/api/v1/auth/login/",
            {"username": "user", "password": "Pass12345!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bootstrap_admin_command_is_idempotent(self):
        with patch.dict(
            "os.environ",
            {
                "DJANGO_SUPERUSER_USERNAME": "render-admin",
                "DJANGO_SUPERUSER_PASSWORD": "RenderStrongPass123!",
                "DJANGO_SUPERUSER_EMAIL": "render@example.com",
            },
        ):
            call_command("bootstrap_admin")
            call_command("bootstrap_admin")

        user = get_user_model().objects.get(username="render-admin")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password("RenderStrongPass123!"))
        self.assertEqual(
            get_user_model().objects.filter(username="render-admin").count(),
            1,
        )

    def test_admin_generates_license_and_audit_log(self):
        self.authenticate_admin()
        response = self.client.post(
            "/api/v1/admin/licenses/",
            {"license_type": "PERMANENT"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertRegex(
            response.data["license_key"],
            r"^MED-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$",
        )
        self.assertTrue(AuditLog.objects.filter(action="LICENSE_CREATED").exists())

    def test_django_admin_save_generates_license_key(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin:licenses_license_add"),
            {
                "license_type": License.Type.PERMANENT,
                "expiry_date_0": "",
                "expiry_date_1": "",
                "hardware_id": "SYSTEMUUIDBIOSSERIAL",
                "is_active": "on",
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        license_obj = License.objects.get(hardware_id="SYSTEMUUIDBIOSSERIAL")
        self.assertRegex(
            license_obj.license_key,
            r"^MED-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$",
        )

    def test_expiry_based_license_requires_future_expiry(self):
        self.authenticate_admin()
        response = self.client.post(
            "/api/v1/admin/licenses/",
            {
                "license_type": "EXPIRY_BASED",
                "expiry_date": (timezone.now() - timedelta(days=1)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_first_activation_binds_hardware_and_repeat_is_allowed(self):
        license_obj = self.create_license()
        payload = {
            "license_key": license_obj.license_key,
            "hardware_id": "HW-001",
        }
        first = self.client.post("/api/v1/activate/", payload, format="json")
        second = self.client.post("/api/v1/activate/", payload, format="json")

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        license_obj.refresh_from_db()
        self.assertEqual(license_obj.hardware_id, "HW-001")
        self.assertEqual(
            ActivationHistory.objects.filter(status="SUCCESS").count(), 2
        )

    def test_activation_endpoint_allows_standalone_browser_cors(self):
        response = self.client.options(
            "/api/v1/activate/",
            HTTP_ORIGIN="https://separate-client.example",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Access-Control-Allow-Origin"], "*")

    def test_sixth_hardware_mismatch_auto_blocks_license(self):
        license_obj = self.create_license(hardware_id="REGISTERED-HW")
        for attempt in range(1, 7):
            response = self.client.post(
                "/api/v1/activate/",
                {
                    "license_key": license_obj.license_key,
                    "hardware_id": f"OTHER-HW-{attempt}",
                },
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        license_obj.refresh_from_db()
        self.assertEqual(license_obj.violation_count, 6)
        self.assertTrue(license_obj.is_blocked)
        self.assertEqual(
            ActivationHistory.objects.filter(status="BLOCKED").count(), 1
        )

    def test_inactive_and_expired_licenses_are_rejected(self):
        inactive = self.create_license(is_active=False)
        response = self.client.post(
            "/api/v1/activate/",
            {
                "license_key": inactive.license_key,
                "hardware_id": "HW",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        inactive.delete()
        expired = self.create_license(
            license_type=License.Type.EXPIRY_BASED,
            expiry_date=timezone.now() - timedelta(minutes=1),
        )
        response = self.client.post(
            "/api/v1/activate/",
            {
                "license_key": expired.license_key,
                "hardware_id": "HW",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
