import secrets
import string

from django.conf import settings


LICENSE_ALPHABET = string.ascii_uppercase + string.digits


def generate_license_key():
    groups = [
        "".join(secrets.choice(LICENSE_ALPHABET) for _ in range(4))
        for _ in range(3)
    ]
    return f"MED-{'-'.join(groups)}"


def get_client_ip(request):
    if getattr(settings, "TRUST_X_FORWARDED_FOR", False):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")

