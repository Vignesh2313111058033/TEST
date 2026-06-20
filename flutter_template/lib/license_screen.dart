import 'package:flutter/material.dart';

import 'license_api.dart';


class LicenseScreen extends StatefulWidget {
  const LicenseScreen({
    required this.hardwareId,
    super.key,
  });

  /// Supply your concatenated system hardware ID + BIOS serial here.
  final String hardwareId;

  @override
  State<LicenseScreen> createState() => _LicenseScreenState();
}


class _LicenseScreenState extends State<LicenseScreen> {
  final _formKey = GlobalKey<FormState>();
  final _licenseController = TextEditingController();
  late final TextEditingController _hardwareController;

  late final LicenseApi _api;
  bool _loading = false;
  LicenseResult? _result;
  String? _error;

  @override
  void initState() {
    super.initState();
    _hardwareController = TextEditingController(text: widget.hardwareId);
    _api = LicenseApi(
      // Use http://10.0.2.2:8000 for the Android emulator.
      baseUrl: 'http://10.0.2.2:8000',
    );
  }

  Future<void> _checkLicense() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _loading = true;
      _result = null;
      _error = null;
    });

    try {
      final result = await _api.validateLicense(
        licenseKey: _licenseController.text,
        hardwareId: _hardwareController.text,
      );
      if (!mounted) return;
      setState(() => _result = result);
    } on LicenseApiException catch (error) {
      if (!mounted) return;
      setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  void dispose() {
    _licenseController.dispose();
    _hardwareController.dispose();
    _api.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final accepted = _result?.accepted == true;

    return Scaffold(
      appBar: AppBar(title: const Text('License Validation')),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 480),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  TextFormField(
                    controller: _licenseController,
                    decoration: const InputDecoration(
                      labelText: 'License key',
                      hintText: 'MED-XXXX-XXXX-XXXX',
                      border: OutlineInputBorder(),
                    ),
                    textCapitalization: TextCapitalization.characters,
                    validator: (value) {
                      final key = value?.trim().toUpperCase() ?? '';
                      final valid = RegExp(
                        r'^MED-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$',
                      ).hasMatch(key);
                      return valid ? null : 'Enter a valid license key.';
                    },
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _hardwareController,
                    decoration: const InputDecoration(
                      labelText: 'Hardware ID + BIOS ID',
                      border: OutlineInputBorder(),
                    ),
                    validator: (value) => value == null || value.trim().isEmpty
                        ? 'Hardware ID is required.'
                        : null,
                  ),
                  const SizedBox(height: 20),
                  FilledButton(
                    onPressed: _loading ? null : _checkLicense,
                    child: Text(_loading ? 'Checking...' : 'Check license'),
                  ),
                  if (_result != null) ...[
                    const SizedBox(height: 20),
                    _MessageCard(
                      success: accepted,
                      message: accepted
                          ? 'SUCCESS: ${_result!.message}'
                          : 'REJECTED: ${_result!.message}',
                    ),
                  ],
                  if (_error != null) ...[
                    const SizedBox(height: 20),
                    _MessageCard(
                      success: false,
                      message: _error!,
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}


class _MessageCard extends StatelessWidget {
  const _MessageCard({
    required this.success,
    required this.message,
  });

  final bool success;
  final String message;

  @override
  Widget build(BuildContext context) {
    final backgroundColor =
        success ? Colors.green.shade50 : Colors.red.shade50;
    final textColor =
        success ? Colors.green.shade800 : Colors.red.shade800;
    return DecoratedBox(
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Text(
          message,
          style: TextStyle(color: textColor),
        ),
      ),
    );
  }
}
