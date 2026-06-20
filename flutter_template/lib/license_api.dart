import 'dart:convert';
import 'dart:async';
import 'dart:io';

import 'package:http/http.dart' as http;


class LicenseResult {
  const LicenseResult({
    required this.accepted,
    required this.status,
    required this.message,
    this.license,
  });

  final bool accepted;
  final String status;
  final String message;
  final Map<String, dynamic>? license;

  factory LicenseResult.fromJson(
    Map<String, dynamic> json, {
    required bool httpSuccess,
  }) {
    final status = json['status']?.toString() ?? 'REJECTED';
    return LicenseResult(
      accepted: httpSuccess && status == 'SUCCESS',
      status: status,
      message: json['message']?.toString() ?? 'License was rejected.',
      license: json['license'] is Map<String, dynamic>
          ? json['license'] as Map<String, dynamic>
          : null,
    );
  }
}


class LicenseApiException implements Exception {
  const LicenseApiException(this.message);

  final String message;

  @override
  String toString() => message;
}


class LicenseApi {
  LicenseApi({
    required this.baseUrl,
    http.Client? client,
  }) : _client = client ?? http.Client();

  /// Android emulator:
  ///   http://10.0.2.2:8000
  ///
  /// Windows/iOS simulator on the same computer:
  ///   http://127.0.0.1:8000
  ///
  /// Physical phone:
  ///   http://YOUR_COMPUTER_LAN_IP:8000
  final String baseUrl;
  final http.Client _client;

  Future<LicenseResult> validateLicense({
    required String licenseKey,
    required String hardwareId,
  }) async {
    final normalizedLicenseKey = licenseKey.trim().toUpperCase();
    final normalizedHardwareId = hardwareId
        .trim()
        .replaceAll(RegExp(r'[^A-Za-z0-9]'), '')
        .toUpperCase();

    if (normalizedLicenseKey.isEmpty || normalizedHardwareId.isEmpty) {
      throw const LicenseApiException(
        'License key and hardware ID are required.',
      );
    }

    final uri = Uri.parse('$baseUrl/api/v1/activate/');

    try {
      final response = await _client
          .post(
            uri,
            headers: const {
              HttpHeaders.contentTypeHeader: 'application/json',
              HttpHeaders.acceptHeader: 'application/json',
            },
            body: jsonEncode({
              'license_key': normalizedLicenseKey,
              'hardware_id': normalizedHardwareId,
            }),
          )
          .timeout(const Duration(seconds: 15));

      Map<String, dynamic> data;
      try {
        data = jsonDecode(response.body) as Map<String, dynamic>;
      } on FormatException {
        throw const LicenseApiException(
          'The licensing server returned an invalid response.',
        );
      }

      return LicenseResult.fromJson(
        data,
        httpSuccess: response.statusCode >= 200 && response.statusCode < 300,
      );
    } on SocketException {
      throw const LicenseApiException(
        'Could not connect to the licensing server.',
      );
    } on HttpException {
      throw const LicenseApiException('Licensing server request failed.');
    } on TimeoutException {
      throw const LicenseApiException('Licensing server request timed out.');
    }
  }

  void close() {
    _client.close();
  }
}
