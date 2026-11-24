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
  late Future<dynamic> history;
  @override void initState() {
    super.initState();
    history = widget.api('books/${widget.bookId}/ai-history/');
  }
  @override void dispose() { question.dispose(); super.dispose(); }
  Future<void> ask() async {
    if (question.text.trim().isEmpty) return;
    setState(() { loading = true; answer = ''; });
    try {
      final response = await widget.api('books/${widget.bookId}/ask/',
          method: 'POST', body: {'question': question.text});
      if (mounted) setState(() {
        answer = response['answer'] ?? 'Javob bo‘sh.';
        history = widget.api('books/${widget.bookId}/ai-history/');
      });
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
      const SizedBox(height: 16),
      const Text('Oldingi suhbatlar', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
      FutureBuilder<dynamic>(future: history, builder: (context, snapshot) {
        if (!snapshot.hasData) return const Text('Suhbatlar yuklanmoqda...');
        final messages = snapshot.data['results'] as List<dynamic>;
        if (messages.isEmpty) return const Text('Hozircha suhbatlar yo‘q.');
        return Column(children: [
          for (final item in messages) ListTile(
            title: Text(item['question'] ?? ''),
            subtitle: Text(item['answer'] ?? '', maxLines: 4, overflow: TextOverflow.ellipsis),
          ),
        ]);
      }),
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
  String submitError = '';
  List<dynamic> feedback = [];
  bool completed = false;
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
    setState(() { busy = true; submitError = ''; });
    try {
      final response = await widget.api('quizzes/${widget.quizId}/submit/',
        method: 'POST', body: {
          'version': data['version'],
          'answers': [for (var i = 0; i < questions.length; i++) answers[i]],
        });
      if (mounted) setState(() {
        completed = true;
        feedback = (response['results'] as List<dynamic>? ?? []);
        result = 'Natija: ${response['score']} / ${response['total']}';
      });
    } catch (e) {
      if (mounted) setState(() => submitError = 'Test yuborilmadi: $e');
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
                onChanged: completed ? null : (v) => setState(() => answers[i] = v!),
              ),
            ],
          )),
        ),
        if (submitError.isNotEmpty) Padding(
          padding: const EdgeInsets.symmetric(vertical: 12),
          child: Text(submitError, style: TextStyle(
            color: Theme.of(context).colorScheme.error)),
        ),
        if (completed) ...[
          Card(
            color: Theme.of(context).colorScheme.primaryContainer,
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(children: [
                const Icon(Icons.emoji_events_outlined, size: 42),
                const SizedBox(height: 8),
                Text(result, style: Theme.of(context).textTheme.headlineSmall),
                const Text('Natijangiz saqlandi'),
              ]),
            ),
          ),
          const SizedBox(height: 12),
          Text('Javoblar tahlili',
            style: Theme.of(context).textTheme.titleLarge),
          for (var i = 0; i < feedback.length; i++)
            Card(
              child: ListTile(
                leading: Icon(feedback[i]['correct'] == true
                  ? Icons.check_circle : Icons.cancel,
                  color: feedback[i]['correct'] == true
                    ? Colors.green : Theme.of(context).colorScheme.error),
                title: Text('${i + 1}. ${feedback[i]['question']}'),
                subtitle: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Javobingiz: ${feedback[i]['chosen']}'),
                    if (feedback[i]['correct'] != true)
                      Text('To‘g‘ri javob: ${feedback[i]['correct_answer']}'),
                    Text(feedback[i]['explanation']?.toString() ?? ''),
                  ],
                ),
              ),
            ),
          OutlinedButton.icon(
            onPressed: () => setState(() {
              completed = false;
              result = '';
              feedback = [];
              answers.clear();
            }),
            icon: const Icon(Icons.refresh),
            label: const Text('Qayta ishlash'),
          ),
        ] else
          FilledButton.icon(
            onPressed: busy ? null : () => submit(data),
            icon: const Icon(Icons.fact_check_outlined),
            label: Text(busy ? 'Saqlanmoqda...' : 'Testni yakunlash'),
          ),
      ]);
    }),
  );
}
