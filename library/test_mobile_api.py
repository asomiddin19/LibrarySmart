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

    def test_categories_are_private(self):
        self.client.logout()
        self.assertEqual(self.client.get('/api/v1/categories/').status_code, 401)
