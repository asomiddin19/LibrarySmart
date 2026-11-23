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
        if (snapshot.hasError) return Center(child: Text('Xatolik: ${snapshot.error}'));
        if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
        final books = snapshot.data['results'] as List<dynamic>;
        return RefreshIndicator(
          onRefresh: () async {
            setState(refresh);
            await shelf;
          },
          child: ListView(children: [
            for (final item in books)
              ListTile(
                leading: Icon(item['favorite'] == true ? Icons.favorite : Icons.menu_book),
                title: Text(item['title'] ?? ''),
                subtitle: Text('Sahifa ${item['page']} / ${item['pages']}'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => widget.openBook(Map<String, dynamic>.from(item)),
              ),
            if (books.isEmpty)
              const ListTile(title: Text('Hali o‘qilgan yoki sevimli kitob yo‘q.')),
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
