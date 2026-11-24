import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:audioplayers/audioplayers.dart';

/// Native audiobook playback for private, size-limited mobile downloads.
class AudiobookPage extends StatefulWidget {
  final String title;
  final Future<Uint8List> Function() fetchAudio;
  const AudiobookPage({super.key, required this.title, required this.fetchAudio});

  @override
  State<AudiobookPage> createState() => _AudiobookPageState();
}

class _AudiobookPageState extends State<AudiobookPage> {
  final player = AudioPlayer();
  bool loading = true;
  bool playing = false;
  String error = '';
  Duration position = Duration.zero;
  Duration duration = Duration.zero;

  @override
  void initState() {
    super.initState();
    player.onPositionChanged.listen((value) {
      if (mounted) setState(() => position = value);
    });
    player.onDurationChanged.listen((value) {
      if (mounted) setState(() => duration = value);
    });
    player.onPlayerStateChanged.listen((state) {
      if (mounted) setState(() => playing = state == PlayerState.playing);
    });
    load();
  }

  Future<void> load() async {
    setState(() { loading = true; error = ''; });
    try {
      final bytes = await widget.fetchAudio();
      if (!mounted) return;
      await player.setSource(BytesSource(bytes));
      if (mounted) setState(() => loading = false);
    } catch (exc) {
      if (mounted) setState(() {
        error = 'Audiokitobni ochib bo‘lmadi: $exc';
        loading = false;
      });
    }
  }

  Future<void> toggle() async {
    try {
      if (playing) {
        await player.pause();
      } else {
        await player.resume();
      }
    } catch (exc) {
      if (mounted) setState(() => error = '$exc');
    }
  }

  String clock(Duration time) {
    final minutes = time.inMinutes.remainder(60).toString().padLeft(2, '0');
    final seconds = time.inSeconds.remainder(60).toString().padLeft(2, '0');
    return '${time.inHours > 0 ? '${time.inHours}:' : ''}$minutes:$seconds';
  }

  @override
  void dispose() {
    player.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Audiokitob')),
    body: SafeArea(child: Center(child: SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 500),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          CircleAvatar(radius: 69,
            backgroundColor: Theme.of(context).colorScheme.primaryContainer,
            child: const Icon(Icons.headphones_rounded, size: 76)),
          const SizedBox(height: 28),
          Text(widget.title,
            style: Theme.of(context).textTheme.headlineSmall,
            textAlign: TextAlign.center),
          const SizedBox(height: 20),
          if (loading) const CircularProgressIndicator(),
          if (error.isNotEmpty) ...[
            Text(error, textAlign: TextAlign.center,
              style: TextStyle(color: Theme.of(context).colorScheme.error)),
            const SizedBox(height: 12),
            FilledButton.icon(onPressed: loading ? null : load,
              icon: const Icon(Icons.refresh), label: const Text('Qayta urinish')),
          ],
          if (!loading && error.isEmpty) ...[
            Slider(
              min: 0,
              max: duration.inMilliseconds > 0
                ? duration.inMilliseconds.toDouble() : 1,
              value: position.inMilliseconds.toDouble().clamp(0,
                duration.inMilliseconds > 0
                  ? duration.inMilliseconds.toDouble() : 1),
              onChanged: duration > Duration.zero
                ? (value) => player.seek(Duration(milliseconds: value.toInt()))
                : null,
            ),
            Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
              Text(clock(position)),
              Text(clock(duration)),
            ]),
            const SizedBox(height: 16),
            Row(mainAxisAlignment: MainAxisAlignment.center, children: [
              IconButton.filledTonal(
                tooltip: '15 soniya orqaga',
                onPressed: () async {
                  final next = position - const Duration(seconds: 15);
                  await player.seek(next.isNegative ? Duration.zero : next);
                },
                icon: const Icon(Icons.replay_10_rounded)),
              const SizedBox(width: 20),
              IconButton.filled(
                iconSize: 44,
                tooltip: playing ? 'Pauza' : 'Eshitish',
                onPressed: toggle,
                icon: Icon(playing ? Icons.pause_rounded : Icons.play_arrow_rounded)),
              const SizedBox(width: 20),
              IconButton.filledTonal(
                tooltip: '15 soniya oldinga',
                onPressed: () async {
                  final next = position + const Duration(seconds: 15);
                  await player.seek(next > duration ? duration : next);
                },
                icon: const Icon(Icons.forward_10_rounded)),
            ]),
            const SizedBox(height: 16),
            const Text('Audiokitob faqat mavjud bo‘lgan kitoblarda ochiladi.'),
          ],
        ]),
      ),
    ))),
  );
}
