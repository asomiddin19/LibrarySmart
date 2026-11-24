/// Secure Library Smart API transport and private reading files.
/// Reusable independently of the mobile screen widgets.
import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

const server = String.fromEnvironment('LIBRARY_API_BASE',
    defaultValue: 'https://librarysmart-api-staging.up.railway.app');

class Api {
  final client = http.Client();
  final storage = const FlutterSecureStorage();
  String baseUrl = server;
  String googleWebClientId = const String.fromEnvironment('GOOGLE_WEB_CLIENT_ID');
  String? cookie;
  String? csrf;
  static const requestTimeout = Duration(seconds: 25);
  Future<void> init() async {
    baseUrl = await storage.read(key: 'server_url') ?? server;
    cookie = await storage.read(key: 'session');
    try {
      final oauth = await client.get(Uri.parse('$baseUrl/api/v1/auth/google/config/')).timeout(requestTimeout);
      if (oauth.statusCode == 200) {
        final config = jsonDecode(oauth.body);
        if (config is Map && config['enabled'] == true && config['web_client_id'] is String) {
          googleWebClientId = config['web_client_id'];
        } else {
          googleWebClientId = '';
        }
      } else {
        googleWebClientId = '';
      }
    } catch (_) {
      googleWebClientId = '';
    }
    final res = await client.get(Uri.parse('$baseUrl/api/v1/auth/csrf/')).timeout(requestTimeout);
    if (res.statusCode != 200) {
      throw Exception('Serverga ulanish xatosi: HTTP ${res.statusCode}');
    }
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
    final response = await client.get(Uri.parse('$candidate/api/v1/health/')).timeout(requestTimeout);
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
  /// Loads a private cover with the active session. Never exposes session tokens
  /// in URL parameters; cap image size before handing bytes to the Flutter decoder.
  Future<Uint8List?> coverBytes(int bookId) async {
    final response = await client.get(
      Uri.parse('$baseUrl/books/$bookId/cover/'),
      headers: {if (cookie != null) 'Cookie': cookie!},
    ).timeout(requestTimeout);
    if (response.statusCode == 404) return null;
    if (response.statusCode != 200) {
      throw Exception('Muqova yuklanmadi: HTTP ${response.statusCode}');
    }
    final mime = response.headers['content-type'] ?? '';
    if (!mime.startsWith('image/') || response.bodyBytes.length > 6 * 1024 * 1024) {
      throw const FormatException('Muqova formati yoki hajmi noto‘g‘ri.');
    }
    return response.bodyBytes;
  }

  /// Private audiobook data. Refuse unexpectedly large downloads on phones.
  /// Only the authenticated API is used; no session tokens are placed in URLs.
  Future<Uint8List> audioBytes(int bookId) async {
    final response = await client.get(
      Uri.parse('$baseUrl/api/v1/books/$bookId/audio/'),
      headers: {if (cookie != null) 'Cookie': cookie!},
    ).timeout(const Duration(seconds: 90));
    if (response.statusCode != 200) {
      throw Exception('Audiokitob yuklanmadi: HTTP ${response.statusCode}');
    }
    final contentType = response.headers['content-type'] ?? '';
    if (!contentType.startsWith('audio/')) {
      throw const FormatException('Server audiokitob formatini qaytarmadi.');
    }
    if (response.bodyBytes.length > 30 * 1024 * 1024) {
      throw const FormatException('Audio 30 MB limitdan katta. Web-pleerdan foydalaning.');
    }
    return response.bodyBytes;
  }

  Future<Uint8List> epubBytes(int bookId) async {
    final response = await client.get(Uri.parse('$baseUrl/api/v1/books/$bookId/epub/'),
      headers: {if (cookie != null) 'Cookie': cookie!}).timeout(const Duration(seconds: 60));
    if (response.statusCode != 200 || !response.headers['content-type'].toString().contains('epub')) {
      throw Exception('EPUB yuklab olinmadi: HTTP ${response.statusCode}');
    }
    return response.bodyBytes;
  }
  Future<Uint8List> pdfBytes(int bookId) async {
    final headers = <String, String>{if (cookie != null) 'Cookie': cookie!};
    final response = await client.get(Uri.parse('$baseUrl/api/v1/books/$bookId/pdf/'), headers: headers).timeout(const Duration(seconds: 60));
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
      ..body = body == null ? '' : jsonEncode(body)).timeout(requestTimeout);
    final full = await http.Response.fromStream(response).timeout(requestTimeout);
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

