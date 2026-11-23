import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:pdfx/pdfx.dart';

class PdfReader extends StatefulWidget {
  final String title;
  final Future<Uint8List> Function() fetchPdf;
  final int initialPage;
  final ValueChanged<int> onPageChanged;
  const PdfReader({
    super.key, required this.title, required this.fetchPdf,
    required this.initialPage, required this.onPageChanged,
  });
  @override
  State<PdfReader> createState() => _PdfReaderState();
}

class _PdfReaderState extends State<PdfReader> {
  late final PdfControllerPinch controller;
  @override
  void initState() {
    super.initState();
    controller = PdfControllerPinch(
      document: _load(),
      initialPage: widget.initialPage.clamp(1, 1000000),
    );
  }
  Future<PdfDocument> _load() async {
    final bytes = await widget.fetchPdf();
    if (bytes.lengthInBytes > 80 * 1024 * 1024) {
      throw StateError('PDF mobil xotira limitidan katta (80 MB).');
    }
    return PdfDocument.openData(bytes);
  }
  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text(widget.title)),
    body: PdfViewPinch(
      controller: controller,
      onPageChanged: widget.onPageChanged,
      onDocumentError: (error) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('PDF ochilmadi: $error')),
        );
      },
    ),
  );
}
