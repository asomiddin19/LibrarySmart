import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:app_links/app_links.dart';
import 'pdf_reader.dart';
import 'epub_reader.dart';
import 'learning_pages.dart';
import 'library_pages.dart';

const server = String.fromEnvironment('LIBRARY_API_BASE',
    defaultValue: 'https://librarysmart-production.up.railway.app');

class Api {
  final client = http.Client();
  final storage = const FlutterSecureStorage();
  String baseUrl = server;
  String? cookie;
  String? csrf;
  Future<void> init() async {
    baseUrl = await storage.read(key: 'server_url') ?? server;
    cookie = await storage.read(key: 'session');
    final res = await client.get(Uri.parse('$baseUrl/api/v1/auth/csrf/'));
    final raw = res.headers['set-cookie'];
    if (raw != null && raw.contains('csrftoken=')) {
      final match = RegExp(r'csrftoken=([^;]+)').firstMatch(raw);
      csrf = match?.group(1);
    }
  }
  Future<void> changeServer(String value) async {
    final uri = Uri.tryParse(value.trim());
    if (uri == null || uri.scheme != 'https' || uri.host.isEmpty ||
        uri.userInfo.isNotEmpty || uri.hasQuery || uri.hasFragment ||
        (uri.path.isNotEmpty && uri.path != '/')) {
      throw const FormatException('Faqat HTTPS server domenini kiriting.');
    }
    final candidate = uri.origin;
    final response = await client.get(Uri.parse('$candidate/api/v1/health/'));
    if (response.statusCode != 200) {
      throw FormatException('Bu manzilda Library Smart API mavjud emas (HTTP ${response.statusCode}).');
    }
    dynamic health;
    try { health = jsonDecode(response.body); } catch (_) {
      throw const FormatException('Server API holatini JSON shaklida qaytarmadi.');
    }
    if (health is! Map || health['status'] != 'ok' || health['api'] != 'v1') {
      throw const FormatException('Manzilda mos Library Smart API topilmadi.');
    }
    baseUrl = candidate;
    cookie = null;
    csrf = null;
    await storage.delete(key: 'session');
    await storage.write(key: 'server_url', value: baseUrl);
    await init();
  }
  Future<Uint8List> epubBytes(int bookId) async {
    final response = await client.get(Uri.parse('$baseUrl/api/v1/books/$bookId/epub/'),
      headers: {if (cookie != null) 'Cookie': cookie!});
    if (response.statusCode != 200 || !response.headers['content-type'].toString().contains('epub')) {
      throw Exception('EPUB yuklab olinmadi: HTTP ${response.statusCode}');
    }
    return response.bodyBytes;
  }
  Future<Uint8List> pdfBytes(int bookId) async {
    final headers = <String, String>{if (cookie != null) 'Cookie': cookie!};
    final response = await client.get(Uri.parse('$baseUrl/api/v1/books/$bookId/pdf/'), headers: headers);
    if (response.statusCode != 200 || !response.headers['content-type'].toString().contains('pdf')) {
      throw Exception('PDF yuklab olinmadi: HTTP ${response.statusCode}');
    }
    return response.bodyBytes;
  }
  Future<dynamic> request(String path, {String method = 'GET', Object? body}) async {
    final uri = Uri.parse('$baseUrl/api/v1/$path');
    final headers = <String, String>{'Accept': 'application/json'};
    if (cookie != null) headers['Cookie'] = cookie!;
    if (csrf != null) {
      headers['X-CSRFToken'] = csrf!;
      headers['Origin'] = baseUrl;
      headers['Cookie'] = [if (cookie != null) cookie!, 'csrftoken=$csrf'].join('; ');
    }
    if (body != null) headers['Content-Type'] = 'application/json';
    final response = await client.send(http.Request(method, uri)
      ..headers.addAll(headers)
      ..body = body == null ? '' : jsonEncode(body));
    final full = await http.Response.fromStream(response);
    final setCookie = full.headers['set-cookie'];
    if (setCookie != null && setCookie.contains('csrftoken=')) {
      csrf = RegExp(r'csrftoken=([^;]+)').firstMatch(setCookie)?.group(1) ?? csrf;
    }
    if (setCookie != null && setCookie.contains('sessionid=')) {
      final match = RegExp(r'sessionid=([^;]+)').firstMatch(setCookie);
      if (match != null) {
        cookie = 'sessionid=${match.group(1)}';
        await storage.write(key: 'session', value: cookie!);
      }
    }
    dynamic data;
    try { data = jsonDecode(full.body); } catch (_) { throw Exception('Server JSON javob qaytarmadi (HTTP ${full.statusCode}).'); }
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
  final navigatorKey = GlobalKey<NavigatorState>();
  StreamSubscription<Uri>? linkSubscription;
  int? pendingBookId;
  bool ready = false;
  bool loggedIn = false;
  @override
  void initState() {
    super.initState();
    linkSubscription = AppLinks().uriLinkStream.listen((uri) {
      if (uri.scheme != 'librarysmart' || uri.host != 'book' || uri.pathSegments.isEmpty) return;
      final id = int.tryParse(uri.pathSegments.first);
      if (id == null || id <= 0) return;
      pendingBookId = id;
      openPendingBook();
    });
    boot();
  }
  Future<void> openPendingBook() async {
    if (!ready || !loggedIn || pendingBookId == null) return;
    final id = pendingBookId!;
    pendingBookId = null;
    try {
      final book = await api.request('books/$id/');
      if (!mounted) return;
      navigatorKey.currentState?.push(MaterialPageRoute(
        builder: (_) => BookDetail(api: api, book: book)));
    } catch (_) {
      if (mounted && navigatorKey.currentContext != null) {
        ScaffoldMessenger.maybeOf(navigatorKey.currentContext!)?.showSnackBar(
          const SnackBar(content: Text('Kitobni ochib bo‘lmadi.')));
      }
    }
  }
  @override
  void dispose() {
    linkSubscription?.cancel();
    api.client.close();
    super.dispose();
  }
  Future<void> boot() async {
    try {
      await api.init();
      await api.request('me/');
      loggedIn = true;
    } catch (_) { loggedIn = false; }
    if (mounted) {
      setState(() => ready = true);
      WidgetsBinding.instance.addPostFrameCallback((_) => openPendingBook());
    }
  }
  @override
  Widget build(BuildContext context) => MaterialApp(
    navigatorKey: navigatorKey,
    title: 'Library Smart',
    theme: ThemeData(useMaterial3: true, colorSchemeSeed: Colors.indigo),
    home: !ready ? const Scaffold(body: Center(child: CircularProgressIndicator()))
      : loggedIn ? Home(api: api, onLogout: () async {
          await api.request('auth/logout/', method: 'POST');
          api.cookie = null;
          await api.storage.delete(key: 'session');
          setState(() => loggedIn = false);
        }) : Login(api: api, onLogin: () {
          setState(() => loggedIn = true);
          WidgetsBinding.instance.addPostFrameCallback((_) => openPendingBook());
        }),
  );
}

class Login extends StatefulWidget {
  final Api api; final VoidCallback onLogin;
  const Login({super.key, required this.api, required this.onLogin});
  @override State<Login> createState() => _LoginState();
}
class _LoginState extends State<Login> {
  static Future<void>? googleInitialization;
  final username = TextEditingController(), password = TextEditingController();
  final serverAddress = TextEditingController();
  String error = ''; bool busy = false;
  @override void initState() { super.initState(); serverAddress.text = widget.api.baseUrl; }
  @override void dispose() { username.dispose(); password.dispose(); serverAddress.dispose(); super.dispose(); }
  Future<void> saveServer() async {
    setState(() { busy = true; error = ''; });
    try {
      await widget.api.changeServer(serverAddress.text);
      if (mounted) setState(() => error = 'Server ulandi. Endi login qiling.');
    } catch (e) {
      if (mounted) setState(() => error = 'Server sozlamasi: $e');
    } finally { if (mounted) setState(() => busy = false); }
  }
  Future<void> googleLogin() async {
    setState(() { busy = true; error = ''; });
    try {
      const clientId = String.fromEnvironment('GOOGLE_WEB_CLIENT_ID');
      if (clientId.isEmpty) throw Exception('GOOGLE_WEB_CLIENT_ID sozlanmagan.');
      final signIn = GoogleSignIn.instance;
      googleInitialization ??= signIn.initialize(serverClientId: clientId);
      await googleInitialization;
      final account = await signIn.authenticate();
      final token = account.authentication.idToken;
      if (token == null) throw Exception('Google ID token kelmadi.');
      await widget.api.request('auth/google/', method: 'POST', body: {'id_token': token});
      widget.onLogin();
    } catch (e) { if (mounted) setState(() => error = e.toString()); }
    finally { if (mounted) setState(() => busy = false); }
  }
  Future<void> register() async {
    setState(() { busy = true; error = ''; });
    try {
      await widget.api.request('auth/signup/', method: 'POST',
        body: {'email': username.text.trim(), 'password': password.text});
      widget.onLogin();
    } catch (e) { if (mounted) setState(() => error = e.toString()); }
    finally { if (mounted) setState(() => busy = false); }
  }
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
          TextField(controller: serverAddress, autocorrect: false,
            decoration: const InputDecoration(labelText: 'Server (HTTPS)',
              hintText: 'https://your-staging.up.railway.app')),
          TextButton(onPressed: busy ? null : saveServer,
            child: const Text('Server manzilini saqlash')),
          const SizedBox(height: 12),
          TextField(controller: username, decoration: const InputDecoration(labelText: 'Email yoki login')),
          TextField(controller: password, obscureText: true,
            decoration: const InputDecoration(labelText: 'Parol')),
          const SizedBox(height: 20), if (error.isNotEmpty) Text(error,
            style: const TextStyle(color: Colors.red)),
          FilledButton(onPressed: busy ? null : submit, child: const Text('Kirish')),
          const SizedBox(height: 8),
          TextButton(onPressed: busy ? null : register,
            child: const Text('Yangi akkaunt yaratish (email + parol)')),
          const SizedBox(height: 8),
          OutlinedButton.icon(onPressed: busy ? null : googleLogin,
            icon: const Icon(Icons.account_circle), label: const Text('Google orqali kirish')),
          const Text('Google Cloud OAuth Client ID sozlanishi kerak.'),
        ])))));
}

class Home extends StatefulWidget {
  final Api api; final Future<void> Function() onLogout;
  const Home({super.key, required this.api, required this.onLogout});
  @override State<Home> createState() => _HomeState();
}
class _HomeState extends State<Home> {
  final search = TextEditingController();
  int page = 1;
  late Future<dynamic> books;

  @override
  void initState() { super.initState(); reload(); }
  @override
  void dispose() { search.dispose(); super.dispose(); }
  void reload() {
    final query = Uri.encodeQueryComponent(search.text.trim());
    books = widget.api.request('books/?page=$page&q=$query');
  }
  void loadPage(int target) {
    setState(() { page = target; reload(); });
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Library Smart Digital'), actions: [
      IconButton(icon: const Icon(Icons.person), tooltip: 'Profil',
        onPressed: () => Navigator.push(context, MaterialPageRoute(
          builder: (_) => ProfilePage(api: widget.api.request)))),
      IconButton(
        icon: const Icon(Icons.bookmark),
        tooltip: 'Mening kutubxonam',
        onPressed: () {
          Navigator.push(context, MaterialPageRoute(
            builder: (shelfContext) => ShelfPage(
              api: widget.api.request,
              openBook: (book) {
                Navigator.push(shelfContext, MaterialPageRoute(
                  builder: (_) => BookDetail(api: widget.api, book: book),
                ));
              },
            ),
          ));
        },
      ),
      IconButton(icon: const Icon(Icons.quiz), tooltip: 'Testlar',
        onPressed: () => Navigator.push(context, MaterialPageRoute(
          builder: (_) => QuizListPage(api: widget.api.request)))),
      IconButton(icon: const Icon(Icons.logout), onPressed: widget.onLogout),
    ]),
    body: Column(children: [
      Padding(padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
        child: TextField(controller: search, textInputAction: TextInputAction.search,
          onSubmitted: (_) => loadPage(1),
          decoration: InputDecoration(labelText: 'Kitob yoki muallifni qidirish',
            prefixIcon: const Icon(Icons.search),
            suffixIcon: IconButton(icon: const Icon(Icons.arrow_forward),
              onPressed: () => loadPage(1)),
            border: const OutlineInputBorder()),
        )),
      Expanded(child: FutureBuilder<dynamic>(future: books, builder: (context, snapshot) {
        if (snapshot.hasError) return Center(child: Text('Xato: ${snapshot.error}'));
        if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
        final data = snapshot.data;
        final entries = data['results'] as List<dynamic>;
        final count = data['count'] as int;
        return RefreshIndicator(onRefresh: () async {
          setState(reload);
          await books;
        }, child: ListView(children: [
          Padding(padding: const EdgeInsets.all(16), child: Text('Elektron kitoblar ($count)',
            style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold))),
          for (final item in entries) ListTile(
            title: Text(item['title'] ?? ''),
            subtitle: Text('${item['author']} • ${item['category']}'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => Navigator.push(context, MaterialPageRoute(
              builder: (_) => BookDetail(api: widget.api, book: item))),
          ),
          if (entries.isEmpty) const ListTile(title: Text('Kitob topilmadi.')),
          Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            TextButton(onPressed: page > 1 ? () => loadPage(page - 1) : null,
              child: const Text('Oldingi')),
            Text('$page / ${(count / 20).ceil().clamp(1, 100000)}'),
            TextButton(onPressed: page * 20 < count ? () => loadPage(page + 1) : null,
              child: const Text('Keyingi')),
          ]),
        ]));
      })),
    ]),
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
        if (newFavorite != null) { favorite = newFavorite; }
        if (newPage != null) { page = newPage; }
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
      Slider(value: page.toDouble().clamp(1.0, ((widget.book['pages'] as int).clamp(1, 100000000)).toDouble()).toDouble(),
        min: 1, max: ((widget.book['pages'] as int).clamp(1, 100000000)).toDouble(),
        divisions: (widget.book['pages'] as int) > 1 ? (widget.book['pages'] as int)-1 : null,
        onChanged: (value) => setState(() => page = value.round()),
        onChangeEnd: (value) => save(newPage: value.round())),
      const SizedBox(height: 12),
      OutlinedButton.icon(
        icon: const Icon(Icons.open_in_browser),
        label: const Text('Web-versiyada ochish'),
        onPressed: () async {
          final uri = Uri.parse('${widget.api.baseUrl}/books/${widget.book['id']}/');
          if (!await launchUrl(uri, mode: LaunchMode.externalApplication) && mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Brauzerni ochib bo‘lmadi.')),
            );
          }
        },
      ),
      if (widget.book['has_pdf'] == true) OutlinedButton.icon(
        icon: const Icon(Icons.auto_awesome),
        label: const Text('AI bilan o‘rganish'),
        onPressed: () => Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => AskBookPage(api: widget.api.request,
            bookId: widget.book['id'] as int, title: widget.book['title']))),
      ),
      if (widget.book['has_epub'] == true) FilledButton.icon(
        icon: const Icon(Icons.chrome_reader_mode),
        label: const Text('EPUB kitobni o‘qish'),
        onPressed: () => Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => EpubReaderPage(
            title: widget.book['title'],
            initialLocator: widget.book['locator'] ?? '',
            fetchEpub: () => widget.api.epubBytes(widget.book['id'] as int),
            onLocatorChanged: (locator) async {
              await widget.api.request('books/${widget.book['id']}/reading/',
                method: 'PUT', body: {'locator': locator});
            },
          ),
        )),
      ),
      if (widget.book['has_pdf'] == true) FilledButton.icon(
        icon: const Icon(Icons.menu_book),
        label: const Text('PDF kitobni o‘qish'),
        onPressed: () => Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => PdfReader(
            title: widget.book['title'], initialPage: page,
            fetchPdf: () => widget.api.pdfBytes(widget.book['id'] as int),
            onPageChanged: (newPage) => save(newPage: newPage),
          ),
        )),
      ),
    ]),
  );
}
