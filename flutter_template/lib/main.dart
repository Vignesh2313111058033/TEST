import 'package:flutter/material.dart';

import 'license_screen.dart';


void main() {
  runApp(const LicenseApp());
}


class LicenseApp extends StatelessWidget {
  const LicenseApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Medical Billing License',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.teal),
        useMaterial3: true,
      ),
      home: const LicenseScreen(
        // Replace this with the value read by your native Windows code.
        hardwareId: 'SYSTEM_UUID_AND_BIOS_SERIAL',
      ),
    );
  }
}

