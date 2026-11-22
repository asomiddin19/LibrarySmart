from django.test import TestCase,SimpleTestCase
from django.contrib.auth.models import User
from django.urls import reverse
from unittest.mock import patch
from .quiz_engine import parse,QuizError,generate
from .models import Quiz,QuizAttempt

SAMPLE="1. DNS vazifasi nima?\nA) Nom yechish\nB) Siqish\nC) Chizish\nD) O‘chirish\nJavob: A\nIzoh: DNS nomni IP ga bog‘laydi."

class ParserTests(SimpleTestCase):
    def test_text_and_json(self):
        import json
        data=parse(SAMPLE)
        self.assertEqual(data[0]["answer"],0)
        self.assertEqual(parse(json.dumps(data)),data)
    def test_invalid(self):
        for raw in ["",SAMPLE.replace("Javob: A","Javob: E"),'[{"question":"Q","options":["a","a","c","d"],"answer":0}]']:
            with self.assertRaises(QuizError):parse(raw)
    def test_mocked_ai(self):
        import json
        payload={"candidates":[{"content":{"parts":[{"text":json.dumps(parse(SAMPLE))}]}}]}
        with patch.dict("os.environ",{"GEMINI_API_KEY":"test"}),patch("library.quiz_engine.urlopen") as url:
            url.return_value.__enter__.return_value.read.return_value=json.dumps(payload).encode()
            self.assertEqual(generate("DNS",1),parse(SAMPLE))

class QuizTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin=User.objects.create_superuser("quizadmin","a@example.test","Password123!")
        cls.student=User.objects.create_user("quizstudent","s@example.test","Password123!")
        cls.other=User.objects.create_user("otherquiz","o@example.test","Password123!")
    def test_publish_take_result_privacy(self):
        self.client.force_login(self.admin)
        r=self.client.post(reverse("quiz_new"),{"title":"DNS test","source":SAMPLE,"action":"save"})
        self.assertEqual(r.status_code,302)
        quiz=Quiz.objects.get();self.assertFalse(quiz.published)
        self.assertContains(self.client.get(reverse("quiz_preview",args=[quiz.pk])),"Nom yechish")
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(reverse("quiz_take",args=[quiz.pk])).status_code,404)
        self.assertEqual(self.client.get(reverse("quiz_new")).status_code,403)
        self.client.force_login(self.admin)
        self.client.post(reverse("quiz_publish",args=[quiz.pk]),{"publish":"1"})
        self.client.force_login(self.student)
        r=self.client.get(reverse("quiz_take",args=[quiz.pk]))
        self.assertEqual(r.status_code,200)
        self.assertNotContains(r,"DNS nomni IP ga bog‘laydi")
        version=r.context["version"]
        self.assertEqual(self.client.post(reverse("quiz_take",args=[quiz.pk]),{"version":version,"q0":"0"}).status_code,302)
        attempt=QuizAttempt.objects.get();self.assertEqual(attempt.percent,100)
        self.assertContains(self.client.get(reverse("quiz_result",args=[attempt.pk])),"100%")
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("quiz_result",args=[attempt.pk])).status_code,403)
    def test_generation_requires_consent(self):
        self.client.force_login(self.admin)
        r=self.client.post(reverse("quiz_new"),{"title":"AI test","source":SAMPLE,"action":"generate","count":"1"})
        self.assertContains(r,"rozilik");self.assertEqual(Quiz.objects.count(),0)
    def test_ai_preview_no_auto_publish(self):
        self.client.force_login(self.admin)
        with patch("library.quiz_views.generate",return_value=parse(SAMPLE)):
            r=self.client.post(reverse("quiz_new"),{"title":"AI test","source":"DNS","action":"generate","count":"1","consent":"1"})
        self.assertContains(r,"Nom yechish");self.assertEqual(Quiz.objects.count(),0)
