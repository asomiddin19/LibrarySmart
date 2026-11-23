import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

const server = String.fromEnvironment('LIBRARY_API_BASE',
    defaultValue: 'https://librarysmart-production.up.railway.app');

class Api {
  final client = http.Client();
  String? cookie;
  String? csrf;
  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    cookie = prefs.getString('session');
    final res = await client.get(Uri.parse('$server/api/v1/auth/csrf/'));
    final raw = res.headers['set-cookie'];
    if (raw != null && raw.contains('csrftoken=')) {
      final match = RegExp(r'csrftoken=([^;]+)').firstMatch(raw);
      csrf = match?.group(1);
    }
  }
  Future<dynamic> request(String path, {String method = 'GET', Object? body}) async {
    final uri = Uri.parse('$server/api/v1/$path');
    final headers = <String, String>{'Accept': 'application/json'};
    if (cookie != null) headers['Cookie'] = cookie!;
    if (csrf != null) {
      headers['X-CSRFToken'] = csrf!;
      headers['Cookie'] = [if (cookie != null) cookie!, 'csrftoken=$csrf'].join('; ');
    }
    if (body != null) headers['Content-Type'] = 'application/json';
    final response = await client.send(http.Request(method, uri)
      ..headers.addAll(headers)
      ..body = body == null ? '' : jsonEncode(body));
    final full = await http.Response.fromStream(response);
    final setCookie = full.headers['set-cookie'];
    if (setCookie != null && setCookie.contains('sessionid=')) {
      final match = RegExp(r'sessionid=([^;]+)').firstMatch(setCookie);
      if (match != null) {
        cookie = 'sessionid=${match.group(1)}';
        (await SharedPreferences.getInstance()).setString('session', cookie!);
      }
    }
    final data = jsonDecode(full.body);
    if (full.statusCode >= 400) throw Exception(data['error'] ?? 'HTTP ${full.statusCode}');
    return data;
  }
}

void main() => runApp(const LibraryApp());

class LibraryApp extends StatefulWidget {
  const LibraryApp({super.key});
  @override
  State<LibraryApp> createState() => _LibraryAppState();
}

class _LibraryAppState extends State<LibraryApp> {
  final api = Api();
  bool ready = false;
  bool loggedIn = false;
  @override
  void initState() { super.initState(); boot(); }
  Future<void> boot() async {
    try {
      await api.init();
      await api.request('me/');
      loggedIn = true;
    } catch (_) { loggedIn = false; }
    if (mounted) setState(() => ready = true);
  }
  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'Library Smart',
    theme: ThemeData(useMaterial3: true, colorSchemeSeed: Colors.indigo),
    home: !ready ? const Scaffold(body: Center(child: CircularProgressIndicator()))
      : loggedIn ? Home(api: api, onLogout: () async {
          await api.request('auth/logout/', method: 'POST');
          api.cookie = null;
          (await SharedPreferences.getInstance()).remove('session');
          setState(() => loggedIn = false);
        }) : Login(api: api, onLogin: () => setState(() => loggedIn = true)),
  );
}

class Login extends StatefulWidget {
  final Api api; final VoidCallback onLogin;
  const Login({super.key, required this.api, required this.onLogin});
  @override State<Login> createState() => _LoginState();
}
class _LoginState extends State<Login> {
  final username = TextEditingController(), password = TextEditingController();
  String error = ''; bool busy = false;
  @override void dispose() { username.dispose(); password.dispose(); super.dispose(); }
  Future<void> submit() async {
    setState(() { busy = true; error = ''; });
    try {
      await widget.api.request('auth/login/', method: 'POST',
          body: {'username': username.text, 'password': password.text});
      widget.onLogin();
    } catch (e) { if (mounted) setState(() => error = e.toString()); }
    finally { if (mounted) setState(() => busy = false); }
  }
  @override Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Library Smart — Kirish')),
    body: Center(child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 440),
      child: Padding(padding: const EdgeInsets.all(24), child: Column(
        mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.menu_book, size: 72), const SizedBox(height: 20),
          TextField(controller: username, decoration: const InputDecoration(labelText: 'Login')),
          TextField(controller: password, obscureText: true,
            decoration: const InputDecoration(labelText: 'Parol')),
          const SizedBox(height: 20), if (error.isNotEmpty) Text(error,
            style: const TextStyle(color: Colors.red)),
          FilledButton(onPressed: busy ? null : submit, child: const Text('Kirish')),
          const SizedBox(height: 8),
          const Text('Google kirish uchun alohida OAuth sozlamalari kerak.'),
        ])))));
}

class Home extends StatefulWidget {
  final Api api; final Future<void> Function() onLogout;
  const Home({super.key, required this.api, required this.onLogout});
  @override State<Home> createState() => _HomeState();
}
class _HomeState extends State<Home> {
  late Future<dynamic> books;
  @override void initState() { super.initState(); books = widget.api.request('books/'); }
  @override Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Library Smart Digital'), actions: [
      IconButton(icon: const Icon(Icons.logout), onPressed: widget.onLogout),
    ]),
    body: FutureBuilder<dynamic>(future: books, builder: (context, snapshot) {
      if (snapshot.hasError) return Center(child: Text('Xato: ${snapshot.error}'));
      if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
      final entries = snapshot.data['results'] as List<dynamic>;
      return RefreshIndicator(onRefresh: () async {
        setState(() => books = widget.api.request('books/')); await books;
      }, child: ListView(children: [
        const Padding(padding: EdgeInsets.all(16), child: Text('Elektron kitoblar',
          style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold))),
        for (final item in entries) ListTile(
          title: Text(item['title'] ?? ''),
          subtitle: Text('${item['author']} • ${item['category']}'),
          trailing: const Icon(Icons.chevron_right),
          onTap: () => Navigator.push(context, MaterialPageRoute(
            builder: (_) => BookDetail(api: widget.api, book: item))),
        ),
        if (entries.isEmpty) const Center(child: Text('Kitob topilmadi.')),
      ]));
    }),
  );
}
class BookDetail extends StatefulWidget {
  final Api api; final dynamic book;
  const BookDetail({super.key, required this.api, required this.book});
  @override State<BookDetail> createState() => _BookDetailState();
}
class _BookDetailState extends State<BookDetail> {
  late bool favorite;
  late int page;
  @override void initState() {
    super.initState(); favorite = widget.book['favorite'] ?? false;
    page = widget.book['page'] ?? 1;
  }
  Future<void> save({bool? newFavorite, int? newPage}) async {
    try {
      await widget.api.request('books/${widget.book['id']}/reading/',
        method: 'PUT', body: {
          if (newFavorite != null) 'favorite': newFavorite,
          if (newPage != null) 'page': newPage,
        });
      if (mounted) setState(() {
        if (newFavorite != null) favorite = newFavorite;
        if (newPage != null) page = newPage;
      });
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())));
    }
  }
  @override Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text(widget.book['title'])),
    body: ListView(padding: const EdgeInsets.all(20), children: [
      Text(widget.book['author'], style: Theme.of(context).textTheme.titleLarge),
      const SizedBox(height: 12),
      Text(widget.book['description'] ?? ''),
      const SizedBox(height: 18),
      SwitchListTile(title: const Text('Sevimli kitob'),
        value: favorite, onChanged: (value) => save(newFavorite: value)),
      Text('O‘qilgan sahifa: $page / ${widget.book['pages']}'),
      Slider(value: page.toDouble().clamp(1.0, (widget.book['pages'] as int).toDouble()),
        min: 1, max: (widget.book['pages'] as int).toDouble().clamp(1.0, double.infinity),
        divisions: (widget.book['pages'] as int) > 1 ? (widget.book['pages'] as int)-1 : null,
        onChanged: (value) => save(newPage: value.round())),
      const SizedBox(height: 12),
      const Text('PDF faylga kirish uchun web o‘quvchidan foydalaning.'),
      SelectableText('$server/books/${widget.book['id']}/read/'),
    ]),
  );
}
