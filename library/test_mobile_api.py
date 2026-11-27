import json
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Book, Quiz, QuizAttempt, Reading

class MobileApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('reader', password='SafePassword123!')
        self.hidden = Book.objects.create(title='Private', author='X', category='IT',
                                          description='Hidden', published=False, pages=2)
        self.book = Book.objects.create(title='Python', author='Author', category='IT',
                                        description='Public', published=True, pages=7)
        self.quiz = Quiz.objects.create(book=self.book, title='Test', published=True,
                                        questions=[{'question': '1+1?', 'options': ['1','2','3','4'],
                                                    'answer': 1, 'explanation': '2'}])
        self.client.force_login(self.user)

    def test_catalog_respects_visibility(self):
        res = self.client.get('/api/v1/books/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()['results']), 1)
        self.assertEqual(self.client.get(f'/api/v1/books/{self.hidden.pk}/').status_code, 404)

    def test_progress_and_favorites_sync(self):
        res = self.client.put(f'/api/v1/books/{self.book.pk}/reading/',
                              json.dumps({'page': 4, 'favorite': True}),
                              content_type='application/json')
        self.assertEqual(res.status_code, 200)
        read = Reading.objects.get(user=self.user, book=self.book)
        self.assertTrue(read.favorite)
        self.assertEqual(read.page, 4)
        self.assertEqual(self.client.get('/api/v1/shelf/').json()['results'][0]['page'], 4)

    def test_no_test_answers_leak(self):
        res = self.client.get(f'/api/v1/quizzes/{self.quiz.pk}/')
        self.assertNotIn('answer', res.content.decode())
        body = {'version': res.json()['version'], 'answers': [1]}
        submit = self.client.post(f'/api/v1/quizzes/{self.quiz.pk}/submit/',
                                  json.dumps(body), content_type='application/json')
        self.assertEqual(submit.status_code, 200)
        self.assertEqual(submit.json()['score'], 1)
        self.assertEqual(QuizAttempt.objects.count(), 1)

    def test_anonymous_access_denied(self):
        self.client.logout()
        self.assertEqual(self.client.get('/api/v1/books/').status_code, 401)

    def test_mobile_signup_and_email_login(self):
        self.client.logout()
        response = self.client.post(
            '/api/v1/auth/signup/',
            json.dumps({'email': 'newreader@example.test', 'password': 'StrongPassword!2406'}),
            content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.client.get('/api/v1/me/').status_code, 200)
        self.client.logout()
        result = self.client.post('/api/v1/auth/login/',
            json.dumps({'username': 'newreader@example.test', 'password': 'StrongPassword!2406'}),
            content_type='application/json')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(self.client.get('/api/v1/me/').json()['email'], 'newreader@example.test')

    def test_duplicate_signup_email_rejected(self):
        self.client.logout()
        response = self.client.post('/api/v1/auth/signup/',
            json.dumps({'email': 'reader@example.test', 'password': 'StrongPassword!2406'}),
            content_type='application/json')
        self.assertEqual(response.status_code, 201)
        response = self.client.post('/api/v1/auth/signup/',
            json.dumps({'email': 'reader@example.test', 'password': 'StrongPassword!2406'}),
            content_type='application/json')
        self.assertEqual(response.status_code, 409)

    def test_catalog_query_count_remains_bounded_with_many_books(self):
        """Each listed book must not trigger an additional Reading query."""
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        for index in range(20):
            item = Book.objects.create(
                title=f'Networking {index}', author='Test author',
                category='IT', description='Performance test',
                published=True, pages=12)
            Reading.objects.create(
                user=self.user, book=item, page=2, favorite=index == 0)
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get('/api/v1/books/?page=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['results']), 20)
        self.assertLessEqual(len(queries), 8,
            f'Catalog query regression: {len(queries)} queries')

    def test_shelf_query_count_remains_bounded_with_many_books(self):
        """Shelf should use select_related and reuse its Reading objects."""
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        for index in range(20):
            item = Book.objects.create(
                title=f'History {index}', author='Test author',
                category='IT', description='Shelf perf test',
                published=True, pages=12)
            Reading.objects.create(
                user=self.user, book=item, page=3, favorite=True)
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get('/api/v1/shelf/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['results']), 20)
        self.assertLessEqual(len(queries), 6,
            f'Shelf query regression: {len(queries)} queries')

    def test_categories_include_only_visible_books_and_counts(self):
        Book.objects.create(title='Linux', author='Demo', category='Linux',
            description='Linux manual', published=True, pages=3)
        Book.objects.create(title='Hidden linux', author='Demo', category='Linux',
            description='Private', published=False, pages=3)
        Book.objects.create(title='Networking', author='Demo', category='Networking',
            description='Network manual', published=True, pages=3)
        response = self.client.get('/api/v1/categories/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['results'], [
            {'name': 'IT', 'count': 1}, {'name': 'Linux', 'count': 1},
            {'name': 'Networking', 'count': 1},
        ])
        response = self.client.get('/api/v1/books/?category=Linux')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)
        self.assertEqual(response.json()['results'][0]['title'], 'Linux')

    def test_three_book_formats_and_category_filters(self):
        from django.core.files.base import ContentFile
        pdf_book = Book.objects.create(
            title='O‘zbek hikoyalari', author='Muallif',
            category='O‘zbek adabiyoti', description='PDF kitob', published=True)
        pdf_book.pdf.save('book.pdf', ContentFile(b'%PDF-1.4 test'), save=True)
        epub_book = Book.objects.create(
            title='Jahon asarlari', author='Muallif',
            category='Jahon adabiyoti', description='EPUB kitob', published=True)
        epub_book.epub.save('book.epub', ContentFile(b'PK test'), save=True)
        audio_book = Book.objects.create(
            title='Bolalar ertaklari', author='Muallif',
            category='Bolalar adabiyoti', description='Audio kitob', published=True)
        audio_book.audio.save('book.mp3', ContentFile(b'ID3 test'), save=True)
        for book_format, expected in [
            ('pdf', pdf_book.pk), ('epub', epub_book.pk), ('audio', audio_book.pk),
        ]:
            response = self.client.get('/api/v1/books/', {'format': book_format})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                [item['id'] for item in response.json()['results']], [expected])
        category_response = self.client.get('/api/v1/books/', {
            'category': 'Bolalar adabiyoti', 'format': 'audio'})
        self.assertEqual(category_response.json()['count'], 1)
        self.assertEqual(category_response.json()['results'][0]['id'], audio_book.pk)
        invalid = self.client.get('/api/v1/books/', {'format': 'exe'})
        self.assertEqual(invalid.status_code, 400)

    def test_categories_are_private(self):
        self.client.logout()
        self.assertEqual(self.client.get('/api/v1/categories/').status_code, 401)

    def test_private_audio_download_and_range(self):
        self.book.audio.save("sample.mp3",
            SimpleUploadedFile("sample.mp3", b"ID3" + b"abcde" * 100,
                               content_type="audio/mpeg"))
        self.book.audio_size = self.book.audio.size
        self.book.save(update_fields=["audio_size"])
        path = f"/api/v1/books/{self.book.pk}/audio/"
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertIn("audio/", response["Content-Type"])
        raw = b"".join(response.streaming_content)
        self.assertTrue(raw.startswith(b"ID3"))
        self.assertEqual(response["Cache-Control"], "private, no-store")
        response = self.client.get(path, HTTP_RANGE="bytes=0-2")
        self.assertEqual(response.status_code, 206)
        self.assertEqual(b"".join(response.streaming_content), b"ID3")
        self.assertEqual(response["Content-Range"], f"bytes 0-2/{len(raw)}")

    def test_private_audio_does_not_leak_to_anonymous_or_hidden(self):
        self.book.audio.save("sample.mp3",
            SimpleUploadedFile("sample.mp3", b"ID3music",
                               content_type="audio/mpeg"))
        self.hidden.audio.save("secret.mp3",
            SimpleUploadedFile("secret.mp3", b"ID3hidden",
                               content_type="audio/mpeg"))
        self.assertEqual(self.client.get(
            f"/api/v1/books/{self.hidden.pk}/audio/").status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(
            f"/api/v1/books/{self.book.pk}/audio/").status_code, 401)
