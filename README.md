# Medical Billing Software Licensing Backend

Django REST Framework backend for issuing licenses, binding the first device,
tracking activation attempts, and automatically blocking suspicious reuse.

## Architecture

```text
config/                 Django settings and root URLs
licenses/
  models.py             License, activation history, and audit tables
  serializers.py        Validation and API representations
  services.py           Atomic activation and audit business logic
  permissions.py        Staff-admin API authorization
  throttles.py          Login and activation rate limits
  views.py              Class-based REST API views
  urls.py               Licensing routes
  admin.py              Django admin registrations
  tests/                API and business-rule tests
schema.sql              PostgreSQL reference schema
```

The `ActivationHistory.license` foreign key is nullable so attempted use of an
unknown key can still be recorded. A real license has many history and audit
records. Deleting a license deletes its activation history; audit records retain
the event but set their license reference to null.

## Setup

Prerequisites: Python 3.12+ and PostgreSQL, or Docker for the included database.

```powershell
.\myvenv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
docker compose up -d db
```

Load `.env` into your shell or set the listed environment variables. For a
quick local SQLite run, set:

```powershell
$env:DB_ENGINE="sqlite"
$env:DJANGO_SECRET_KEY="local-development-secret"
```

Apply migrations and create the first administrator:

```powershell
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Run tests without PostgreSQL:

```powershell
$env:DB_ENGINE="sqlite"
python manage.py test
```

## API endpoints

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| POST | `/api/v1/auth/login/` | Public | Admin JWT login |
| POST | `/api/v1/auth/refresh/` | Public | Refresh access token |
| POST | `/api/v1/activate/` | Public, throttled | Client activation/validation |
| GET, POST | `/api/v1/admin/licenses/` | Admin | List or generate licenses |
| GET, PATCH, PUT | `/api/v1/admin/licenses/{key}/` | Admin | View or update license |
| POST | `/api/v1/admin/licenses/{key}/activate/` | Admin | Mark active |
| POST | `/api/v1/admin/licenses/{key}/deactivate/` | Admin | Mark inactive |
| POST | `/api/v1/admin/licenses/{key}/block/` | Admin | Block |
| POST | `/api/v1/admin/licenses/{key}/unblock/` | Admin | Unblock |
| GET | `/api/v1/admin/activation-history/` | Admin | All activation history |
| GET | `/api/v1/admin/suspicious-attempts/` | Admin | Hardware mismatch attempts |
| GET | `/api/v1/admin/audit-logs/` | Admin | Administrative audit trail |

License list filters: `license_type`, `is_active`, `is_blocked`, and `search`.
History filters: `license_key` and `status`. List APIs are paginated.

## Request and response examples

Admin login:

```http
POST /api/v1/auth/login/
Content-Type: application/json

{"username":"admin","password":"StrongPassword"}
```

```json
{
  "refresh": "<refresh-token>",
  "access": "<access-token>",
  "user": {"id": 1, "username": "admin"}
}
```

Generate a permanent license:

```http
POST /api/v1/admin/licenses/
Authorization: Bearer <access-token>
Content-Type: application/json

{"license_type":"PERMANENT"}
```

Generate an expiry-based license:

```json
{
  "license_type": "EXPIRY_BASED",
  "expiry_date": "2027-12-31T23:59:59Z"
}
```

Example result:

```json
{
  "id": 1,
  "license_key": "MED-A1B2-C3D4-E5F6",
  "license_type": "PERMANENT",
  "created_at": "2026-06-20T10:30:00Z",
  "expiry_date": null,
  "hardware_id": null,
  "is_active": true,
  "is_blocked": false,
  "violation_count": 0,
  "is_expired": false
}
```

First activation:

```http
POST /api/v1/activate/
Content-Type: application/json

{
  "license_key": "MED-A1B2-C3D4-E5F6",
  "hardware_id": "SYSTEMUUIDBIOSSERIAL"
}
```

```json
{
  "status": "SUCCESS",
  "message": "License activated.",
  "license": {
    "license_key": "MED-A1B2-C3D4-E5F6",
    "hardware_id": "SYSTEMUUIDBIOSSERIAL"
  }
}
```

A mismatched device receives HTTP 400 with `REJECTED`. Its attempt is stored
and `violation_count` increments atomically. The sixth mismatch changes the
license to `is_blocked=true` and returns HTTP 403 with `BLOCKED`.

## Windows sample client

An ordinary browser cannot read BIOS or system identifiers. Run the included
PowerShell launcher, which reads the Windows system UUID and BIOS serial,
concatenates them, and opens `sample.html` through Django:

```powershell
.\launch-sample.ps1
```

The page submits only `license_key` and the generated `hardware_id` to the
activation API and displays `SUCCESS` or `REJECTED`.

## Security notes

- Only active staff users can receive an admin JWT or call dashboard APIs.
- Activation and login have separate rate limits.
- First activation and violation updates run in database transactions with row
  locking to prevent concurrent device-binding races.
- License keys use cryptographically secure random characters.
- Administrative state changes are persisted in `AuditLog` and emitted through
  the `licenses.audit` logger.
- Enable `TRUST_X_FORWARDED_FOR` only behind a trusted reverse proxy that
  overwrites client forwarding headers.
- Production deployments must use HTTPS, a strong secret key, restricted
  allowed hosts, database backups, and proxy-level rate limiting.

## Deploy to Render

The repository includes `render.yaml` and `build.sh`. The Blueprint provisions
the Django web service and a PostgreSQL database.

1. Push this project to a GitHub, GitLab, or Bitbucket repository.
2. In Render, select **New > Blueprint**.
3. Connect the repository containing this project.
4. Keep the Blueprint path as `render.yaml` and select **Deploy Blueprint**.
5. Wait for the database, build, migrations, static collection, and web deploy
   to finish.
6. Open the generated `https://medical-licensing-api-....onrender.com` URL.

During Blueprint creation, Render prompts for
`DJANGO_SUPERUSER_PASSWORD`. Enter a strong password. The build creates the
`admin` account once and does not reset its password on later deploys. You can
change the username or email in `render.yaml` before deployment.

Then open:

```text
https://YOUR-RENDER-HOST/django-admin/
```

For a Flutter production build, replace the local API URL with:

```dart
baseUrl: 'https://YOUR-RENDER-HOST'
```

Do not include a trailing slash. Render's free PostgreSQL database expires
after 30 days and has no backups; use a paid database for persistent production
licensing data.
