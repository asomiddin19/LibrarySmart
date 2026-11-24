import 'package:flutter/material.dart';
import 'learning_pages.dart';

class ShelfPage extends StatefulWidget {
  final ApiCall api;
  final void Function(Map<String, dynamic>) openBook;
  const ShelfPage({super.key, required this.api, required this.openBook});
  @override State<ShelfPage> createState() => _ShelfPageState();
}
class _ShelfPageState extends State<ShelfPage> {
  late Future<dynamic> shelf;
  @override
  void initState() { super.initState(); refresh(); }
  void refresh() { shelf = widget.api('shelf/'); }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Mening kutubxonam')),
    body: FutureBuilder<dynamic>(
      future: shelf,
      builder: (context, snapshot) {
        if (snapshot.hasError) return Center(child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            const Icon(Icons.wifi_off_rounded, size: 48),
            const SizedBox(height: 12),
            const Text('Shaxsiy javonni ochib bo‘lmadi.'),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: () => setState(refresh),
              icon: const Icon(Icons.refresh),
              label: const Text('Qayta urinish')),
          ]),
        ));
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }
        final books = snapshot.data['results'] as List<dynamic>;
        final favorites = books.where((book) => book['favorite'] == true).length;
        return RefreshIndicator(
          onRefresh: () async {
            setState(refresh);
            await shelf;
          },
          child: ListView(padding: const EdgeInsets.all(14), children: [
            Card(
              color: Theme.of(context).colorScheme.primaryContainer,
              child: Padding(padding: const EdgeInsets.all(19),
                child: Row(children: [
                  const Icon(Icons.bookmarks_rounded, size: 36),
                  const SizedBox(width: 16),
                  Expanded(child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Mening kitob javonim',
                        style: Theme.of(context).textTheme.titleLarge),
                      Text('${books.length} ta kitob · $favorites ta sevimli'),
                    ],
                  )),
                ]),
              ),
            ),
            const SizedBox(height: 13),
            if (books.isEmpty) Padding(
              padding: const EdgeInsets.all(28),
              child: Column(children: [
                const Icon(Icons.bookmark_add_outlined, size: 54),
                const SizedBox(height: 12),
                Text('Javoningiz hali bo‘sh',
                  style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 6),
                const Text('Kitoblarni sevimliga qo‘shing yoki o‘qishni boshlang.',
                  textAlign: TextAlign.center),
              ]),
            ),
            for (final item in books)
              Card(margin: const EdgeInsets.only(bottom: 9), child: ListTile(
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 14, vertical: 9),
                leading: CircleAvatar(child: Icon(
                  item['favorite'] == true
                    ? Icons.favorite_rounded : Icons.auto_stories_outlined)),
                title: Text(item['title']?.toString() ?? '',
                  maxLines: 2, overflow: TextOverflow.ellipsis),
                subtitle: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SizedBox(height: 5),
                    Text('Sahifa ${item['page']} / ${item['pages']}'),
                    const SizedBox(height: 7),
                    LinearProgressIndicator(value: (
                      ((item['page'] as num?)?.toDouble() ?? 1) /
                      (((item['pages'] as num?)?.toDouble() ?? 1)
                        .clamp(1.0, 10000000.0))
                    ).clamp(0.0, 1.0).toDouble()),
                  ],
                ),
                trailing: const Icon(Icons.chevron_right_rounded),
                onTap: () => widget.openBook(Map<String, dynamic>.from(item)),
              )),
          ]),
        );
      },
    ),
  );
}

class ResultsPage extends StatefulWidget {
  final ApiCall api;
  const ResultsPage({super.key, required this.api});
  @override State<ResultsPage> createState() => _ResultsPageState();
}
class _ResultsPageState extends State<ResultsPage> {
  late final Future<dynamic> result;
  @override void initState() { super.initState(); result = widget.api('results/'); }
  @override Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Test natijalarim')),
    body: FutureBuilder<dynamic>(future: result, builder: (context, snapshot) {
      if (snapshot.hasError) return Center(child: Text('Xatolik: ${snapshot.error}'));
      if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
      final attempts = snapshot.data['results'] as List<dynamic>;
      return ListView(children: [
        for (final attempt in attempts)
          ListTile(
            leading: const Icon(Icons.fact_check),
            title: Text(attempt['quiz'] ?? ''),
            subtitle: Text(attempt['created']?.toString().split('T').first ?? ''),
            trailing: Text('${attempt['score']} / ${attempt['total']}'),
          ),
        if (attempts.isEmpty) const ListTile(title: Text('Test natijasi yo‘q.')),
      ]);
    }),
  );
}

class ProfilePage extends StatelessWidget {
  final ApiCall api;
  const ProfilePage({super.key, required this.api});
  @override Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Profilim')),
    body: FutureBuilder<dynamic>(future: api('me/'), builder: (context, snapshot) {
      if (snapshot.hasError) return Center(child: Text('${snapshot.error}'));
      if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
      final user = snapshot.data;
      return ListView(padding: const EdgeInsets.all(16), children: [
        const CircleAvatar(radius: 32, child: Icon(Icons.person, size: 32)),
        const SizedBox(height: 16),
        ListTile(title: Text(user['name'] ?? ''), subtitle: const Text('Foydalanuvchi')),
        ListTile(title: Text(user['email'] ?? ''), subtitle: const Text('Email')),
        ListTile(title: Text(user['username'] ?? ''), subtitle: const Text('Login')),
        FilledButton.tonalIcon(
          onPressed: () => Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => ResultsPage(api: api))),
          icon: const Icon(Icons.fact_check), label: const Text('Test natijalarim')),
      ]);
    }),
  );
}
