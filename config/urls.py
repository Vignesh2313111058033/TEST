from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenRefreshView

from licenses.views import AdminTokenObtainPairView


@api_view(["GET"])
@permission_classes([AllowAny])
def api_home(request):
    return Response(
        {
            "name": "Medical Billing Licensing API",
            "status": "running",
            "endpoints": {
                "admin_login": request.build_absolute_uri("/api/v1/auth/login/"),
                "token_refresh": request.build_absolute_uri("/api/v1/auth/refresh/"),
                "license_activation": request.build_absolute_uri("/api/v1/activate/"),
                "sample_client": request.build_absolute_uri("/sample/"),
                "licenses": request.build_absolute_uri("/api/v1/admin/licenses/"),
                "activation_history": request.build_absolute_uri(
                    "/api/v1/admin/activation-history/"
                ),
                "django_admin": request.build_absolute_uri("/django-admin/"),
            },
        }
    )


urlpatterns = [
    path("", api_home, name="api-home"),
    path("sample/", TemplateView.as_view(template_name="sample.html"), name="sample"),
    path("django-admin/", admin.site.urls),
    path("api/v1/auth/login/", AdminTokenObtainPairView.as_view(), name="admin-login"),
    path("api/v1/auth/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("api/v1/", include("licenses.urls")),
]
