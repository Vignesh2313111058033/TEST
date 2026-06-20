# Flutter licensing API template

This template calls:

```text
POST /api/v1/activate/
```

Request:

```json
{
  "license_key": "MED-XXXX-XXXX-XXXX",
  "hardware_id": "SYSTEMUUIDBIOSSERIAL"
}
```

Accepted response:

```json
{
  "status": "SUCCESS",
  "message": "License activated.",
  "license": {}
}
```

Rejected responses use HTTP 400 or 403 with `REJECTED` or `BLOCKED`.

## Use the template

Copy `lib/license_api.dart` and `lib/license_screen.dart` into your Flutter
project and add the HTTP package:

```powershell
flutter pub add http
```

Or run this standalone template:

```powershell
cd flutter_template
flutter pub get
flutter run
```

## Backend URL

Set `baseUrl` in `license_screen.dart`:

| Flutter target | Backend URL |
|---|---|
| Android emulator | `http://10.0.2.2:8000` |
| Windows desktop | `http://127.0.0.1:8000` |
| iOS simulator | `http://127.0.0.1:8000` |
| Physical device | `http://COMPUTER_LAN_IP:8000` |

For a physical device, run Django on the network:

```powershell
python manage.py runserver 0.0.0.0:8000
```

Add the computer's LAN IP to `DJANGO_ALLOWED_HOSTS` and allow port 8000 through
the Windows firewall.

## Android development configuration

Add internet permission to `android/app/src/main/AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.INTERNET" />
```

Local HTTP is not suitable for production. For development only, add
`android:usesCleartextTraffic="true"` to the `<application>` element:

```xml
<application
    android:label="medical_license_sample"
    android:usesCleartextTraffic="true">
```

Use HTTPS in production and remove cleartext traffic.

## Hardware ID

Flutter/Dart cannot reliably read a Windows BIOS serial by itself. Read the
system UUID and BIOS serial in a Windows native plugin or platform channel,
concatenate them, strip non-alphanumeric characters, and pass the result into:

```dart
LicenseScreen(hardwareId: combinedHardwareId)
```

The API service normalizes the value again before sending it.

