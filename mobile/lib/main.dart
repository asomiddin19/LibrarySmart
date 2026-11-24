import 'dart:async';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:app_links/app_links.dart';
import 'pdf_reader.dart';
import 'audiobook_page.dart';
import 'epub_reader.dart';
import 'learning_pages.dart';
import 'library_pages.dart';
import 'api_client.dart';
import 'catalog_dashboard.dart';

final ValueNotifier<ThemeMode> libraryTheme = ValueNotifier(ThemeMode.system);

Future<void> updateLibraryTheme(ThemeMode mode) async {
  libraryTheme.value = mode;
  final prefs = await SharedPreferences.getInstance();
  await prefs.setString('library_theme_mode', mode.name);
}

Widget libraryThemeAction() => ValueListenableBuilder<ThemeMode>(
  valueListenable: libraryTheme,
  builder: (context, mode, _) => IconButton(
    tooltip: mode == ThemeMode.dark ? 'Yorug‘ rejim' : 'Tungi rejim',
    icon: Icon(mode == ThemeMode.dark
      ? Icons.light_mode_outlined : Icons.dark_mode_outlined),
    onPressed: () => updateLibraryTheme(
      mode == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark),
  ),
);

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
      final prefs = await SharedPreferences.getInstance();
      final savedMode = prefs.getString('library_theme_mode');
      libraryTheme.value = ThemeMode.values.firstWhere(
        (mode) => mode.name == savedMode, orElse: () => ThemeMode.system);
    } catch (_) { /* System theme remains available. */ }
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
  Widget build(BuildContext context) => ValueListenableBuilder<ThemeMode>(
    valueListenable: libraryTheme,
    builder: (context, mode, _) => MaterialApp(
    navigatorKey: navigatorKey,
    title: 'Library Smart',
    themeMode: mode,
    theme: ThemeData(useMaterial3: true, colorSchemeSeed: Colors.indigo,
      brightness: Brightness.light),
    darkTheme: ThemeData(useMaterial3: true, colorSchemeSeed: Colors.teal,
      brightness: Brightness.dark),
    home: !ready ? const Scaffold(body: Center(child: CircularProgressIndicator()))
      : loggedIn ? Home(api: api, onLogout: () async {
          try {
            await api.request('auth/logout/', method: 'POST');
          } finally {
            // A network outage must never prevent local sign-out.
            api.cookie = null;
            api.csrf = null;
            await api.storage.delete(key: 'session');
            if (mounted) setState(() => loggedIn = false);
          }
        }) : Login(api: api, onLogin: () {
          setState(() => loggedIn = true);
          WidgetsBinding.instance.addPostFrameCallback((_) => openPendingBook());
        }),
    ),
  );
}

class Login extends StatefulWidget {
  final Api api;
  final VoidCallback onLogin;
  const Login({super.key, required this.api, required this.onLogin});

  @override
  State<Login> createState() => _LoginState();
}

class _LoginState extends State<Login> {
  static Future<void>? googleInitialization;
  final username = TextEditingController();
  final password = TextEditingController();
  final serverAddress = TextEditingController();
  String error = '';
  bool busy = false;
  bool showPassword = false;

  @override
  void initState() {
    super.initState();
    serverAddress.text = widget.api.baseUrl;
  }

  @override
  void dispose() {
    username.dispose();
    password.dispose();
    serverAddress.dispose();
    super.dispose();
  }

  Future<void> saveServer() async {
    setState(() { busy = true; error = ''; });
    try {
      await widget.api.changeServer(serverAddress.text);
      if (mounted) setState(() => error = 'Server ulandi. Endi hisobingizga kiring.');
    } catch (e) {
      if (mounted) setState(() => error = 'Serverga ulanish xatosi: $e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> googleLogin() async {
    setState(() { busy = true; error = ''; });
    try {
      if (widget.api.csrf == null) await widget.api.init();
      final clientId = widget.api.googleWebClientId;
      if (clientId.isEmpty) throw Exception('Google orqali kirish hali sozlanmagan.');
      final signIn = GoogleSignIn.instance;
      googleInitialization ??= signIn.initialize(serverClientId: clientId);
      await googleInitialization;
      final account = await signIn.authenticate();
      final token = account.authentication.idToken;
      if (token == null) throw Exception('Google ID token kelmadi.');
      await widget.api.request('auth/google/', method: 'POST',
          body: {'id_token': token});
      widget.onLogin();
    } catch (e) {
      if (mounted) setState(() => error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> submit() async {
    if (username.text.trim().isEmpty || password.text.isEmpty) {
      setState(() => error = 'Email (yoki login) va parolni kiriting.');
      return;
    }
    setState(() { busy = true; error = ''; });
    try {
      if (widget.api.csrf == null) await widget.api.init();
      await widget.api.request('auth/login/', method: 'POST',
          body: {'username': username.text.trim(), 'password': password.text});
      widget.onLogin();
    } catch (e) {
      if (mounted) setState(() => error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Library Smart'),
      actions: [libraryThemeAction()]),
    body: SafeArea(child: Center(child: SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 440),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const CircleAvatar(
            radius: 37,
            child: Icon(Icons.auto_stories_rounded, size: 42),
          ),
          const SizedBox(height: 14),
          Text('Xush kelibsiz!', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 6),
          const Text('Elektron kutubxonangizga kiring',
              textAlign: TextAlign.center),
          const SizedBox(height: 26),
          TextField(
            controller: username,
            keyboardType: TextInputType.emailAddress,
            autofillHints: const [AutofillHints.email, AutofillHints.username],
            textInputAction: TextInputAction.next,
            decoration: const InputDecoration(
              labelText: 'Email yoki login',
              prefixIcon: Icon(Icons.person_outline),
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 14),
          TextField(
            controller: password,
            obscureText: !showPassword,
            autofillHints: const [AutofillHints.password],
            textInputAction: TextInputAction.done,
            onSubmitted: (_) => busy ? null : submit(),
            decoration: InputDecoration(
              labelText: 'Parol',
              prefixIcon: const Icon(Icons.lock_outline),
              border: const OutlineInputBorder(),
              suffixIcon: IconButton(
                tooltip: showPassword ? 'Parolni yashirish' : 'Parolni ko‘rsatish',
                icon: Icon(showPassword ? Icons.visibility_off : Icons.visibility),
                onPressed: () => setState(() => showPassword = !showPassword),
              ),
            ),
          ),
          if (error.isNotEmpty) Padding(
            padding: const EdgeInsets.only(top: 14),
            child: Text(error, textAlign: TextAlign.center,
                style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ),
          const SizedBox(height: 20),
          if (busy) const CircularProgressIndicator(),
          const SizedBox(height: 8),
          SizedBox(width: double.infinity, child: FilledButton.icon(
            onPressed: busy ? null : submit,
            icon: const Icon(Icons.login),
            label: const Text('Kirish'),
          )),
          const SizedBox(height: 12),
          SizedBox(width: double.infinity, child: OutlinedButton.icon(
            icon: const Icon(Icons.person_add_alt_1),
            label: const Text('Ro‘yxatdan o‘tish'),
            onPressed: busy ? null : () => Navigator.push(context,
              MaterialPageRoute(builder: (_) => RegisterPage(
                api: widget.api, onRegistered: widget.onLogin))),
          )),
          if (widget.api.googleWebClientId.isNotEmpty) ...[
            const SizedBox(height: 12),
            SizedBox(width: double.infinity, child: OutlinedButton.icon(
              onPressed: busy ? null : googleLogin,
              icon: const Icon(Icons.account_circle),
              label: const Text('Google orqali kirish'),
            )),
          ],
          const SizedBox(height: 24),
          ExpansionTile(
            leading: const Icon(Icons.settings_outlined),
            title: const Text('Server sozlamalari'),
            childrenPadding: const EdgeInsets.only(bottom: 12),
            children: [
              TextField(
                controller: serverAddress,
                autocorrect: false,
                keyboardType: TextInputType.url,
                decoration: const InputDecoration(
                  labelText: 'HTTPS server manzili',
                  border: OutlineInputBorder(),
                ),
              ),
              TextButton(onPressed: busy ? null : saveServer,
                child: const Text('Serverni tekshirish va saqlash')),
            ],
          ),
        ]),
      ),
    ))),
  );
}

class RegisterPage extends StatefulWidget {
  final Api api;
  final VoidCallback onRegistered;
  const RegisterPage({super.key, required this.api, required this.onRegistered});

  @override
  State<RegisterPage> createState() => _RegisterPageState();
}

class _RegisterPageState extends State<RegisterPage> {
  final email = TextEditingController();
  final password = TextEditingController();
  final repeatPassword = TextEditingController();
  bool busy = false;
  bool showPassword = false;
  String error = '';

  @override
  void dispose() {
    email.dispose();
    password.dispose();
    repeatPassword.dispose();
    super.dispose();
  }

  Future<void> register() async {
    final address = email.text.trim();
    if (!RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$').hasMatch(address)) {
      setState(() => error = 'To‘g‘ri email manzilini kiriting.');
      return;
    }
    if (password.text.length < 8) {
      setState(() => error = 'Parol kamida 8 belgidan iborat bo‘lishi kerak.');
      return;
    }
    if (password.text != repeatPassword.text) {
      setState(() => error = 'Ikkala parol bir xil emas.');
      return;
    }
    setState(() { busy = true; error = ''; });
    try {
      if (widget.api.csrf == null) await widget.api.init();
      await widget.api.request('auth/signup/', method: 'POST',
        body: {'email': address, 'password': password.text});
      if (!mounted) return;
      Navigator.of(context).pop();
      widget.onRegistered();
    } catch (e) {
      if (mounted) setState(() => error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Ro‘yxatdan o‘tish')),
    body: SafeArea(child: Center(child: SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 440),
        child: Column(mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          const Icon(Icons.person_add_alt_1, size: 62),
          const SizedBox(height: 12),
          Text('Yangi akkaunt yarating',
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 22),
          TextField(
            controller: email,
            keyboardType: TextInputType.emailAddress,
            autofillHints: const [AutofillHints.email],
            decoration: const InputDecoration(
              labelText: 'Email manzilingiz',
              prefixIcon: Icon(Icons.mail_outline),
              border: OutlineInputBorder(),
            )),
          const SizedBox(height: 14),
          TextField(
            controller: password,
            obscureText: !showPassword,
            decoration: InputDecoration(
              labelText: 'Yangi parol',
              prefixIcon: const Icon(Icons.lock_outline),
              border: const OutlineInputBorder(),
              suffixIcon: IconButton(
                onPressed: () => setState(() => showPassword = !showPassword),
                icon: Icon(showPassword ? Icons.visibility_off : Icons.visibility),
              ),
            )),
          const SizedBox(height: 14),
          TextField(
            controller: repeatPassword,
            obscureText: !showPassword,
            decoration: const InputDecoration(
              labelText: 'Parolni qayta kiriting',
              prefixIcon: Icon(Icons.lock_reset),
              border: OutlineInputBorder(),
            )),
          const SizedBox(height: 10),
          const Text('Kamida 8 belgi, harf va raqamlardan foydalaning. '
              'Juda oddiy yoki keng tarqalgan parollar qabul qilinmaydi.'),
          if (error.isNotEmpty) Padding(
            padding: const EdgeInsets.only(top: 12),
            child: Text(error, textAlign: TextAlign.center,
                style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ),
          const SizedBox(height: 18),
          if (busy) const Center(child: CircularProgressIndicator()),
          FilledButton.icon(
            onPressed: busy ? null : register,
            icon: const Icon(Icons.check_circle_outline),
            label: const Text('Akkaunt yaratish')),
          const SizedBox(height: 10),
          TextButton(
            onPressed: busy ? null : () => Navigator.of(context).pop(),
            child: const Text('Akkauntim bor — kirishga qaytish')),
        ]),
      ),
    ))),
  );
}

class Home extends StatelessWidget {
  final Api api;
  final Future<void> Function() onLogout;
  const Home({super.key, required this.api, required this.onLogout});

  void openShelf(BuildContext context) {
    Navigator.push(context, MaterialPageRoute(
      builder: (shelfContext) => ShelfPage(
        api: api.request,
        openBook: (book) => Navigator.push(shelfContext, MaterialPageRoute(
          builder: (_) => BookDetail(api: api, book: book))),
      )));
  }

  void openQuiz(BuildContext context) => Navigator.push(context,
    MaterialPageRoute(builder: (_) => QuizListPage(api: api.request)));

  void openProfile(BuildContext context) => Navigator.push(context,
    MaterialPageRoute(builder: (_) => ProfilePage(api: api.request)));

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(Icons.auto_stories_rounded),
        SizedBox(width: 10),
        Text('Library Smart'),
      ]),
      actions: [
        libraryThemeAction(),
        IconButton(icon: const Icon(Icons.person_outline_rounded),
          tooltip: 'Profil', onPressed: () => openProfile(context)),
        IconButton(icon: const Icon(Icons.logout_rounded),
          tooltip: 'Chiqish', onPressed: onLogout),
      ],
    ),
    bottomNavigationBar: NavigationBar(
      selectedIndex: 0,
      onDestinationSelected: (index) {
        if (index == 1) openShelf(context);
        if (index == 2) openQuiz(context);
        if (index == 3) openProfile(context);
      },
      destinations: const [
        NavigationDestination(icon: Icon(Icons.auto_stories_outlined),
          selectedIcon: Icon(Icons.auto_stories), label: 'Kitoblar'),
        NavigationDestination(icon: Icon(Icons.bookmark_border),
          selectedIcon: Icon(Icons.bookmark), label: 'Javonim'),
        NavigationDestination(icon: Icon(Icons.quiz_outlined),
          selectedIcon: Icon(Icons.quiz), label: 'Testlar'),
        NavigationDestination(icon: Icon(Icons.person_outline),
          selectedIcon: Icon(Icons.person), label: 'Profil'),
      ],
    ),
    body: CatalogDashboard(
      api: api,
      openBook: (book) => Navigator.push(context, MaterialPageRoute(
        builder: (_) => BookDetail(api: api, book: book))),
      openShelf: () => openShelf(context),
      openQuizzes: () => openQuiz(context),
    ),
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
          final opened = await launchUrl(uri, mode: LaunchMode.externalApplication);
          if (!mounted) return;
          if (!opened) {
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
      if (widget.book['has_audio'] == true) FilledButton.icon(
        icon: const Icon(Icons.headphones_rounded),
        label: const Text('Audiokitobni tinglash'),
        onPressed: () => Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => AudiobookPage(
            title: widget.book['title'],
            fetchAudio: () => widget.api.audioBytes(widget.book['id'] as int),
          ),
        )),
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
