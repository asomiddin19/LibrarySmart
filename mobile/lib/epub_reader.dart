import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:epub_view/epub_view.dart';

class EpubReaderPage extends StatefulWidget {
  final String title;
  final String initialLocator;
  final Future<Uint8List> Function() fetchEpub;
  final Future<void> Function(String) onLocatorChanged;
  const EpubReaderPage({
    super.key, required this.title, required this.initialLocator,
    required this.fetchEpub, required this.onLocatorChanged,
  });
  @override
  State<EpubReaderPage> createState() => _EpubReaderPageState();
}
class _EpubReaderPageState extends State<EpubReaderPage> {
  late final EpubController controller;
  String? lastSaved;

  @override
  void initState() {
    super.initState();
    controller = EpubController(
      document: _fetch(),
      epubCfi: widget.initialLocator.isEmpty ? null : widget.initialLocator,
    );
  }
  Future<EpubBook> _fetch() async {
    final bytes = await widget.fetchEpub();
    if (bytes.length > 80 * 1024 * 1024) {
      throw StateError('EPUB hajmi 80 MB limitdan oshdi.');
    }
    return EpubDocument.openData(bytes);
  }
  @override
  void dispose() { controller.dispose(); super.dispose(); }
  void persist() {
    final cfi = controller.generateEpubCfi();
    if (cfi == null || cfi.isEmpty || cfi == lastSaved || cfi.length > 1024) return;
    lastSaved = cfi;
    widget.onLocatorChanged(cfi).catchError((Object error) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('O‘qish joyi saqlanmadi: $error')));
    });
  }
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Text(widget.title),
      actions: [
        IconButton(icon: const Icon(Icons.bookmark_add), tooltip: 'O‘qish joyini saqlash',
          onPressed: persist),
      ],
    ),
    body: EpubView(
      controller: controller,
      onChapterChanged: (_) => persist(),
      onDocumentError: (error) {
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('EPUB ochilmadi: $error')));
      },
    ),
  );
}
