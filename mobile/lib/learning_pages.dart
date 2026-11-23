import 'package:flutter/material.dart';

typedef ApiCall = Future<dynamic> Function(String path, {String method, Object? body});

class AskBookPage extends StatefulWidget {
  final int bookId;
  final String title;
  final ApiCall api;
  const AskBookPage({super.key, required this.bookId, required this.title, required this.api});
  @override State<AskBookPage> createState() => _AskBookPageState();
}

class _AskBookPageState extends State<AskBookPage> {
  final question = TextEditingController();
  String answer = '';
  bool loading = false;
  @override void dispose() { question.dispose(); super.dispose(); }
  Future<void> ask() async {
    if (question.text.trim().isEmpty) return;
    setState(() { loading = true; answer = ''; });
    try {
      final response = await widget.api('books/${widget.bookId}/ask/',
          method: 'POST', body: {'question': question.text});
      if (mounted) setState(() => answer = response['answer'] ?? 'Javob bo‘sh.');
    } catch (e) {
      if (mounted) setState(() => answer = 'AI xatosi: $e');
    } finally { if (mounted) setState(() => loading = false); }
  }
  @override Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text('AI — ${widget.title}')),
    body: ListView(padding: const EdgeInsets.all(20), children: [
      const Text('Kitobdan savol bering. AI xato qilishi mumkin; sahifani tekshiring.'),
      const SizedBox(height: 12),
      TextField(controller: question, maxLines: 3,
        decoration: const InputDecoration(border: OutlineInputBorder(),
          hintText: 'Masalan: Bu bobning asosiy g‘oyasi nima?')),
      const SizedBox(height: 12),
      FilledButton(onPressed: loading ? null : ask,
        child: Text(loading ? 'Javob olinmoqda...' : 'AI yordamchidan so‘rash')),
      const SizedBox(height: 20),
      SelectableText(answer, style: Theme.of(context).textTheme.bodyLarge),
    ]),
  );
}

class QuizListPage extends StatefulWidget {
  final ApiCall api;
  const QuizListPage({super.key, required this.api});
  @override State<QuizListPage> createState() => _QuizListPageState();
}
class _QuizListPageState extends State<QuizListPage> {
  late final Future<dynamic> quizzes;
  @override void initState() {
    super.initState();
    quizzes = widget.api('quizzes/');
  }
  @override Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Testlar markazi')),
    body: FutureBuilder<dynamic>(future: quizzes, builder: (context, snapshot) {
      if (snapshot.hasError) return Center(child: Text('Xatolik: ${snapshot.error}'));
      if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
      final results = snapshot.data['results'] as List<dynamic>;
      return ListView(children: [
        for (final q in results) ListTile(
          title: Text(q['title'] ?? ''),
          subtitle: Text('${q['question_count']} savol'),
          onTap: () => Navigator.push(context, MaterialPageRoute(
            builder: (_) => QuizPage(api: widget.api, quizId: q['id'] as int))),
        ),
        if (results.isEmpty) const ListTile(title: Text('Hozircha test yo‘q.')),
      ]);
    }),
  );
}

class QuizPage extends StatefulWidget {
  final ApiCall api;
  final int quizId;
  const QuizPage({super.key, required this.api, required this.quizId});
  @override State<QuizPage> createState() => _QuizPageState();
}
class _QuizPageState extends State<QuizPage> {
  late final Future<dynamic> quiz;
  final Map<int, int> answers = {};
  bool busy = false;
  String result = '';
  @override void initState() {
    super.initState();
    quiz = widget.api('quizzes/${widget.quizId}/');
  }
  Future<void> submit(dynamic data) async {
    final questions = data['questions'] as List<dynamic>;
    if (answers.length != questions.length) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Barcha savollarga javob bering.')));
      return;
    }
    setState(() => busy = true);
    try {
      final response = await widget.api('quizzes/${widget.quizId}/submit/',
        method: 'POST', body: {
          'version': data['version'],
          'answers': [for (var i = 0; i < questions.length; i++) answers[i]],
        });
      if (mounted) setState(() => result =
        'Natija: ${response['score']} / ${response['total']}');
    } catch (e) {
      if (mounted) setState(() => result = 'Xatolik: $e');
    } finally { if (mounted) setState(() => busy = false); }
  }
  @override Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Test ishlash')),
    body: FutureBuilder<dynamic>(future: quiz, builder: (context, snapshot) {
      if (snapshot.hasError) return Center(child: Text('${snapshot.error}'));
      if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
      final data = snapshot.data;
      final questions = data['questions'] as List<dynamic>;
      return ListView(padding: const EdgeInsets.all(16), children: [
        Text(data['title'], style: Theme.of(context).textTheme.headlineSmall),
        for (var i = 0; i < questions.length; i++) Card(
          child: Padding(padding: const EdgeInsets.all(12), child: Column(
            crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${i + 1}. ${questions[i]['question']}',
                style: const TextStyle(fontWeight: FontWeight.bold)),
              for (var j = 0; j < 4; j++) RadioListTile<int>(
                title: Text(questions[i]['options'][j]),
                value: j, groupValue: answers[i],
                onChanged: result.isNotEmpty ? null : (v) => setState(() => answers[i] = v!),
              ),
            ],
          )),
        ),
        if (result.isNotEmpty) Text(result,
          style: Theme.of(context).textTheme.titleLarge),
        FilledButton(onPressed: busy || result.isNotEmpty ? null : () => submit(data),
          child: const Text('Testni yakunlash')),
      ]);
    }),
  );
}
