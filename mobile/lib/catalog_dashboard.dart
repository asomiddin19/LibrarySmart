import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'api_client.dart';

/// Dashboard uses live catalog data; it never displays imaginary books.
class CatalogDashboard extends StatefulWidget {
  final Api api;
  final Future<void> Function(dynamic book) openBook;
  final VoidCallback openShelf;
  final VoidCallback openQuizzes;
  const CatalogDashboard({
    super.key, required this.api, required this.openBook,
    required this.openShelf, required this.openQuizzes,
  });

  @override
  State<CatalogDashboard> createState() => _CatalogDashboardState();
}

class _CatalogDashboardState extends State<CatalogDashboard> {
  final search = TextEditingController();
  final coverLoads = <int, Future<Uint8List?>>{};
  final knownCategories = <String>{};
  late Future<dynamic> books;
  late Future<dynamic> categoriesFuture;
  String category = '';
  String format = 'all';
  int page = 1;

  @override
  void initState() {
    super.initState();
    categoriesFuture = widget.api.request('categories/');
    load();
  }

  void load() {
    final query = Uri(queryParameters: {
      'page': '$page',
      if (search.text.trim().isNotEmpty) 'q': search.text.trim(),
      if (category.isNotEmpty) 'category': category,
      if (format != 'all') 'format': format,
    }).query;
    books = widget.api.request('books/?$query');
  }

  void refresh() => setState(load);

  void chooseCategory(String value) {
    setState(() {
      category = value;
      page = 1;
      load();
    });
  }

  void chooseFormat(String value) {
    setState(() {
      format = value;
      page = 1;
      load();
    });
  }

  Future<void> openBook(dynamic book) async {
    await widget.openBook(book);
    if (mounted) refresh();
  }

  @override
  void dispose() {
    search.dispose();
    super.dispose();
  }

  Widget cover(dynamic book, {double? width, double? height}) {
    final id = book['id'] as int;
    final hasCover = book['has_cover'] == true;
    final shade = Colors.primaries[id.abs() % Colors.primaries.length];
    final fallback = Container(
      width: width, height: height,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft, end: Alignment.bottomRight,
          colors: [shade.shade800, shade.shade500],
        ),
      ),
      alignment: Alignment.center,
      padding: const EdgeInsets.all(14),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center, children: [
          const Icon(Icons.auto_stories_rounded, color: Colors.white, size: 42),
          const SizedBox(height: 10),
          Text(book['title']?.toString() ?? 'Kitob',
            maxLines: 3, overflow: TextOverflow.ellipsis,
            textAlign: TextAlign.center,
            style: const TextStyle(color: Colors.white, fontSize: 13,
              fontWeight: FontWeight.bold, height: 1.2)),
        ],
      ),
    );
    if (!hasCover) return fallback;
    final loader = coverLoads.putIfAbsent(id, () => widget.api.coverBytes(id));
    return FutureBuilder<Uint8List?>(
      future: loader, builder: (context, snapshot) {
        if (!snapshot.hasData || snapshot.data == null) return fallback;
        return Image.memory(snapshot.data!, width: width, height: height,
          fit: BoxFit.cover, errorBuilder: (_, __, ___) => fallback);
      },
    );
  }

  Widget bookCard(dynamic book) {
    final pages = (book['pages'] as num?)?.toInt() ?? 1;
    final current = (book['page'] as num?)?.toInt() ?? 1;
    final progress = (current / pages.clamp(1, 10000000)).clamp(0.0, 1.0).toDouble();
    final theme = Theme.of(context);
    return InkWell(
      borderRadius: BorderRadius.circular(18),
      onTap: () => openBook(book),
      child: Card(
        margin: EdgeInsets.zero,
        clipBehavior: Clip.antiAlias,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18),
          side: BorderSide(color: theme.colorScheme.outlineVariant.withValues(alpha: .5))),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Expanded(child: Stack(fit: StackFit.expand, children: [
            cover(book),
            if (book['favorite'] == true)
              const Positioned(top: 9, right: 9,
                child: CircleAvatar(radius: 16, backgroundColor: Colors.white,
                  child: Icon(Icons.favorite, color: Colors.deepOrange, size: 18))),
          ])),
          Padding(
            padding: const EdgeInsets.fromLTRB(10, 10, 10, 4),
            child: Text(book['title']?.toString() ?? '',
              maxLines: 2, overflow: TextOverflow.ellipsis,
              style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700)),
          ),
          Padding(padding: const EdgeInsets.symmetric(horizontal: 10),
            child: Text(book['author']?.toString() ?? '',
              maxLines: 1, overflow: TextOverflow.ellipsis,
              style: theme.textTheme.bodySmall)),
          Padding(padding: const EdgeInsets.fromLTRB(10, 8, 10, 10),
            child: Row(children: [
              Expanded(child: ClipRRect(borderRadius: BorderRadius.circular(6),
                child: LinearProgressIndicator(value: progress, minHeight: 5))),
              const SizedBox(width: 8),
              if (book['has_pdf'] == true)
                const Icon(Icons.picture_as_pdf_rounded, size: 17, color: Colors.redAccent),
              if (book['has_epub'] == true)
                const Padding(padding: EdgeInsets.only(left: 5),
                  child: Icon(Icons.menu_book_rounded, size: 17, color: Colors.teal)),
              if (book['has_audio'] == true)
                const Padding(padding: EdgeInsets.only(left: 5),
                  child: Icon(Icons.headphones_rounded, size: 17, color: Colors.deepPurple)),
            ])),
        ]),
      ),
    );
  }

  Widget hero(int count, dynamic currentBook) {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 12, 16, 8),
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        gradient: const LinearGradient(
          begin: Alignment.topLeft, end: Alignment.bottomRight,
          colors: [Color(0xFF152D70), Color(0xFF256F83)],
        ),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Row(children: [
          Icon(Icons.auto_stories_rounded, color: Color(0xFF8EEBDD), size: 28),
          SizedBox(width: 9),
          Text('LIBRARY SMART',
            style: TextStyle(color: Color(0xFFB9F5EE), letterSpacing: 1.6,
              fontSize: 12, fontWeight: FontWeight.w800)),
        ]),
        const SizedBox(height: 14),
        const Text('Bilim olami siz bilan',
          style: TextStyle(color: Colors.white,
            fontSize: 25, fontWeight: FontWeight.w800)),
        const SizedBox(height: 7),
        Text('$count ta elektron kitob · PDF, EPUB va audio',
          style: const TextStyle(color: Color(0xFFD7EAF6), fontSize: 13)),
        const SizedBox(height: 16),
        Wrap(spacing: 9, runSpacing: 8, children: [
          FilledButton.icon(
            onPressed: currentBook == null ? widget.openShelf
              : () => openBook(currentBook),
            icon: const Icon(Icons.play_arrow_rounded),
            label: Text(currentBook == null ? 'Kutubxonam' : 'Davom ettirish')),
          OutlinedButton.icon(
            onPressed: widget.openQuizzes,
            style: OutlinedButton.styleFrom(
              foregroundColor: Colors.white,
              side: const BorderSide(color: Color(0xFFB4D9E8))),
            icon: const Icon(Icons.quiz_outlined),
            label: const Text('Testlar')),
        ]),
      ]),
    );
  }

  String _connectionMessage(Object? error) {
    final message = error.toString().toLowerCase();
    if (message.contains('failed host lookup') ||
        message.contains('socketexception') ||
        message.contains('no address associated with hostname')) {
      return 'Server manzili topilmadi (DNS xatosi). Internet yoki DNS '
          'sozlamalarini tekshirib, qayta urinib ko‘ring. '
          'Server: ${widget.api.baseUrl}';
    }
    if (message.contains('timeout')) {
      return 'Server vaqtida javob bermadi. Ulanishni tekshirib, '
          'qayta urinib ko‘ring.';
    }
    if (message.contains('401') || message.contains('403')) {
      return 'Sessiya eskirgan yoki ruxsat yetarli emas. '
          'Akkauntdan chiqib, qayta kiring.';
    }
    return 'Kitoblar yuklanmadi: ${error.toString()}';
  }

  Widget loading() => const Center(child: CircularProgressIndicator());

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(children: [
      Padding(padding: const EdgeInsets.fromLTRB(16, 12, 16, 2),
        child: SearchBar(
          controller: search,
          hintText: 'Kitob nomi yoki muallifni qidiring',
          leading: const Icon(Icons.search),
          padding: const WidgetStatePropertyAll(
            EdgeInsets.symmetric(horizontal: 16)),
          trailing: [IconButton(
            tooltip: 'Qidirish',
            icon: const Icon(Icons.arrow_forward_rounded),
            onPressed: () { page = 1; refresh(); },
          )],
          onSubmitted: (_) { page = 1; refresh(); },
        )),
      Expanded(child: FutureBuilder<dynamic>(
        future: books,
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return Center(child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                const Icon(Icons.wifi_off_rounded, size: 52),
                const SizedBox(height: 15),
                Text('Kutubxonaga ulanishda muammo',
                  style: theme.textTheme.titleMedium, textAlign: TextAlign.center),
                const SizedBox(height: 10),
                Text(
                  _connectionMessage(snapshot.error),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 12),
                FilledButton.icon(onPressed: refresh,
                  icon: const Icon(Icons.refresh), label: const Text('Qayta urinish')),
                const SizedBox(height: 12),
                Text(
                  'Wi-Fi va mobil internetni almashtirib ko‘ring. '
                  'Telefon brauzerida server manzilini ochib tekshiring. '
                  'Agar ikkala tarmoqda ham ochilmasa, server domeni yoki DNS '
                  'bilan muammo bo‘lishi mumkin.',
                  textAlign: TextAlign.center,
                  style: theme.textTheme.bodySmall,
                ),
              ]),
            ));
          }
          if (!snapshot.hasData) return loading();
          final data = snapshot.data as Map<String, dynamic>;
          final entries = (data['results'] as List<dynamic>? ?? []);
          final count = (data['count'] as num?)?.toInt() ?? 0;
          for (final b in entries) {
            final c = b['category']?.toString() ?? '';
            if (c.isNotEmpty) knownCategories.add(c);
          }
          final continuing = entries.where((b) =>
            (b['page'] as num? ?? 1) > 1).toList();
          final currentBook = continuing.isEmpty ? null : continuing.first;
          return RefreshIndicator(
            onRefresh: () async {
              refresh();
              await books;
            },
            child: LayoutBuilder(builder: (context, constraints) {
              final width = constraints.maxWidth;
              final columns = width >= 680 ? 4 : width >= 460 ? 3 : 2;
              return ListView(children: [
                hero(count, currentBook),
                if (currentBook != null)
                  Padding(padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
                    child: Card(
                      child: ListTile(
                        leading: const Icon(Icons.bookmark_added_outlined),
                        title: const Text('O‘qishni davom ettirish'),
                        subtitle: Text(currentBook['title']?.toString() ?? ''),
                        trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                        onTap: () => openBook(currentBook),
                      ),
                    )),
                Padding(padding: const EdgeInsets.fromLTRB(16, 18, 16, 8),
                  child: Text('Kitob turlari',
                    style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800))),
                SizedBox(height: 54,
                  child: ListView(scrollDirection: Axis.horizontal,
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    children: [
                      for (final option in const [
                        ('all', 'Barchasi', Icons.library_books_outlined),
                        ('pdf', 'PDF', Icons.picture_as_pdf_rounded),
                        ('epub', 'EPUB', Icons.menu_book_rounded),
                        ('audio', 'Audio', Icons.headphones_rounded),
                      ])
                        Padding(padding: const EdgeInsets.symmetric(horizontal: 4),
                          child: ChoiceChip(
                            avatar: Icon(option.$3, size: 18),
                            label: Text(option.$2),
                            selected: format == option.$1,
                            onSelected: (_) => chooseFormat(option.$1),
                          )),
                    ])),
                Padding(padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                  child: Text('Kategoriyalar',
                    style: theme.textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w800))),
                SizedBox(height: 48, child: FutureBuilder<dynamic>(
                  future: categoriesFuture,
                  builder: (context, categoriesSnapshot) {
                    final items = (categoriesSnapshot.hasData
                      ? (categoriesSnapshot.data['results'] as List<dynamic>? ?? [])
                      : <dynamic>[]);
                    final names = items.isNotEmpty
                      ? items.map((item) => item['name'].toString()).toList()
                      : knownCategories.toList()..sort();
                    return ListView(
                      scrollDirection: Axis.horizontal,
                      padding: const EdgeInsets.symmetric(horizontal: 12),
                      children: [
                        for (final c in ['', ...names])
                          Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 4),
                            child: ChoiceChip(
                              label: Text(c.isEmpty ? 'Barchasi' : c),
                              selected: category == c,
                              onSelected: (_) => chooseCategory(c),
                            ),
                          ),
                      ],
                    );
                  },
                )),
                Padding(padding: const EdgeInsets.fromLTRB(16, 18, 16, 12),
                  child: Row(children: [
                    Expanded(child: Text('Elektron kitoblar',
                      style: theme.textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.w800))),
                    Text('$count ta', style: theme.textTheme.labelLarge),
                  ])),
                if (entries.isEmpty)
                  Padding(padding: const EdgeInsets.all(28),
                    child: Column(children: [
                      const Icon(Icons.library_books_outlined, size: 52),
                      const SizedBox(height: 12),
                      Text(category.isEmpty
                        ? 'Hozircha kitoblar yo‘q'
                        : 'Bu kategoriyada kitob topilmadi',
                        style: theme.textTheme.titleMedium),
                      const SizedBox(height: 10),
                      TextButton(onPressed: () => chooseCategory(''),
                        child: const Text('Barcha kitoblarni ko‘rish')),
                    ]))
                else
                  Padding(padding: const EdgeInsets.symmetric(horizontal: 12),
                    child: GridView.builder(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: entries.length,
                      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: columns, crossAxisSpacing: 11,
                        mainAxisSpacing: 13, childAspectRatio: .62),
                      itemBuilder: (context, i) => bookCard(entries[i]),
                    )),
                const SizedBox(height: 16),
                if (count > 20)
                  Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                    TextButton(
                      onPressed: page > 1 ? () {
                        setState(() { page--; load(); });
                      } : null, child: const Text('Oldingi')),
                    Text('$page / ${(count / 20).ceil()}'),
                    TextButton(onPressed: page * 20 < count ? () {
                      setState(() { page++; load(); });
                    } : null, child: const Text('Keyingi')),
                  ]),
                const SizedBox(height: 36),
              ]);
            }),
          );
        },
      )),
    ]);
  }
}
