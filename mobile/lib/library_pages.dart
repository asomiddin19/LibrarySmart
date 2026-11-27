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

class ProfilePage extends StatefulWidget {
  final ApiCall api;
  const ProfilePage({super.key, required this.api});
  @override State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  late Future<dynamic> profile;
  final firstName = TextEditingController();
  final lastName = TextEditingController();
  bool editing = false;
  bool saving = false;
  String message = '';

  @override
  void initState() {
    super.initState();
    refresh();
  }

  void refresh() { profile = widget.api('me/'); }

  @override
  void dispose() {
    firstName.dispose();
    lastName.dispose();
    super.dispose();
  }

  Future<void> save() async {
    setState(() { saving = true; message = ''; });
    try {
      await widget.api('me/', method: 'PATCH', body: {
        'first_name': firstName.text.trim(), 'last_name': lastName.text.trim(),
      });
      if (mounted) setState(() {
        editing = false;
        message = 'Profil muvaffaqiyatli saqlandi.';
        refresh();
      });
    } catch (e) {
      if (mounted) setState(() => message = 'Xatolik: $e');
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Profilim')),
    body: FutureBuilder<dynamic>(
      future: profile,
      builder: (context, snapshot) {
        if (snapshot.hasError) return Center(child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Text('Profil yuklanmadi: ${snapshot.error}'),
            const SizedBox(height: 12),
            FilledButton.icon(onPressed: () => setState(refresh),
              icon: const Icon(Icons.refresh), label: const Text('Qayta urinish')),
          ]),
        ));
        if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
        final user = snapshot.data as Map<String, dynamic>;
        return ListView(padding: const EdgeInsets.all(20), children: [
          Center(child: CircleAvatar(radius: 43,
            child: Text((user['first_name']?.toString().isNotEmpty == true
                ? user['first_name'].toString()[0]
                : user['username'].toString()[0]).toUpperCase(),
              style: Theme.of(context).textTheme.headlineLarge))),
          const SizedBox(height: 10),
          Text(user['name']?.toString() ?? '',
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 22),
          Card(child: Column(children: [
            ListTile(leading: const Icon(Icons.mail_outline),
              title: Text(user['email']?.toString() ?? ''),
              subtitle: const Text('Elektron pochta')),
            ListTile(leading: const Icon(Icons.account_circle_outlined),
              title: Text(user['username']?.toString() ?? ''),
              subtitle: const Text('Login')),
          ])),
          const SizedBox(height: 18),
          if (editing) ...[
            TextField(controller: firstName,
              decoration: const InputDecoration(
                border: OutlineInputBorder(), labelText: 'Ism')),
            const SizedBox(height: 12),
            TextField(controller: lastName,
              decoration: const InputDecoration(
                border: OutlineInputBorder(), labelText: 'Familiya')),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: saving ? null : save,
              icon: const Icon(Icons.save_outlined),
              label: Text(saving ? 'Saqlanmoqda...' : 'Saqlash')),
            TextButton(onPressed: saving ? null : () => setState(() => editing = false),
              child: const Text('Bekor qilish')),
          ] else
            FilledButton.tonalIcon(
              onPressed: () => setState(() {
                firstName.text = user['first_name']?.toString() ?? '';
                lastName.text = user['last_name']?.toString() ?? '';
                editing = true;
                message = '';
              }),
              icon: const Icon(Icons.edit_outlined),
              label: const Text('Profilni tahrirlash')),
          if (message.isNotEmpty)
            Padding(padding: const EdgeInsets.all(12),
              child: Text(message, textAlign: TextAlign.center)),
          const SizedBox(height: 12),
          if (user['has_password'] == true)
            OutlinedButton.icon(
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => ChangePasswordPage(api: widget.api))),
              icon: const Icon(Icons.lock_reset_outlined),
              label: const Text('Parolni o‘zgartirish')),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => ResultsPage(api: widget.api))),
            icon: const Icon(Icons.fact_check_outlined),
            label: const Text('Test natijalarim')),
        ]);
      },
    ),
  );
}

class ChangePasswordPage extends StatefulWidget {
  final ApiCall api;
  const ChangePasswordPage({super.key, required this.api});
  @override State<ChangePasswordPage> createState() => _ChangePasswordPageState();
}

class _ChangePasswordPageState extends State<ChangePasswordPage> {
  final oldPassword = TextEditingController();
  final newPassword = TextEditingController();
  final confirmPassword = TextEditingController();
  bool saving = false;
  String error = '';

  @override
  void dispose() {
    oldPassword.dispose();
    newPassword.dispose();
    confirmPassword.dispose();
    super.dispose();
  }

  Future<void> submit() async {
    if (newPassword.text != confirmPassword.text) {
      setState(() => error = 'Yangi parollar bir-biriga mos emas.');
      return;
    }
    setState(() { saving = true; error = ''; });
    try {
      await widget.api('auth/password/change/', method: 'POST', body: {
        'old_password': oldPassword.text,
        'new_password': newPassword.text,
      });
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Parolingiz yangilandi.')));
      Navigator.pop(context);
    } catch (e) {
      if (mounted) setState(() => error = '$e');
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Parolni o‘zgartirish')),
    body: SafeArea(child: ListView(
      padding: const EdgeInsets.all(22),
      children: [
        const Icon(Icons.lock_reset, size: 55),
        const SizedBox(height: 22),
        TextField(
          controller: oldPassword, obscureText: true,
          decoration: const InputDecoration(border: OutlineInputBorder(),
            labelText: 'Joriy parol')),
        const SizedBox(height: 14),
        TextField(
          controller: newPassword, obscureText: true,
          decoration: const InputDecoration(border: OutlineInputBorder(),
            labelText: 'Yangi parol')),
        const SizedBox(height: 14),
        TextField(
          controller: confirmPassword, obscureText: true,
          decoration: const InputDecoration(border: OutlineInputBorder(),
            labelText: 'Yangi parolni tasdiqlang')),
        const SizedBox(height: 12),
        const Text('Kuchli, boshqa hisoblarda ishlatilmagan parol tanlang.'),
        if (error.isNotEmpty) Padding(
          padding: const EdgeInsets.all(12),
          child: Text(error,
            style: TextStyle(color: Theme.of(context).colorScheme.error))),
        const SizedBox(height: 18),
        FilledButton.icon(onPressed: saving ? null : submit,
          icon: const Icon(Icons.check),
          label: Text(saving ? 'Saqlanmoqda...' : 'Parolni yangilash')),
      ],
    )),
  );
}
