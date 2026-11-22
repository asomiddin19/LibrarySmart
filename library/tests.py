from django.test import TestCase,override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from pypdf import PdfWriter
from tempfile import TemporaryDirectory
from .models import Book,Reading,Review

class ElectronicTests(TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        override=override_settings(MEDIA_ROOT=self.tmp.name)
        override.enable();self.addCleanup(override.disable)
        self.admin=User.objects.create_superuser("admin","admin@example.test","TestPassword!123")
        self.student=User.objects.create_user("student","student@example.test","TestPassword!123")
        self.client.force_login(self.admin)
        self.payload={"title":"Python","author":"Demo","category":"IT","language":"O‘zbek","description":"O‘quv qo‘llanma","published":"on"}
        self.client.post(reverse("book_add"),{**self.payload,"pdf":self.valid_pdf()})
        self.book=Book.objects.get()
    def valid_pdf(self):
        buf=BytesIO();writer=PdfWriter()
        for _ in range(3): writer.add_blank_page(width=200,height=300)
        writer.write(buf)
        return SimpleUploadedFile("demo.pdf",buf.getvalue(),content_type="application/pdf")
    def test_upload(self):
        self.assertEqual(self.book.pages,3)
        self.assertGreater(self.book.file_size,0)
    def test_reject_non_pdf(self):
        r=self.client.post(reverse("book_add"),{**self.payload,"pdf":SimpleUploadedFile("fake.pdf",b"hello")})
        self.assertContains(r,"PDF o‘qib bo‘lmaydi")
        self.assertEqual(Book.objects.count(),1)
    def test_student_permissions(self):
        self.client.force_login(self.student)
        for name in ["book_add","readers","audit"]: self.assertEqual(self.client.get(reverse(name)).status_code,403)
    def test_pdf_open_download(self):
        self.client.force_login(self.student)
        r=self.client.get(reverse("pdf",args=[self.book.pk]))
        self.assertEqual(r["Content-Type"],"application/pdf");self.assertEqual(r["X-Frame-Options"],"SAMEORIGIN")
        self.assertTrue(b"".join(r.streaming_content).startswith(b"%PDF-"))
        r=self.client.get(reverse("download",args=[self.book.pk]))
        self.assertIn("attachment",r["Content-Disposition"]);self.assertTrue(b"".join(r.streaming_content).startswith(b"%PDF-"))
        self.book.refresh_from_db();self.assertEqual(self.book.downloads,1)
    def test_hidden_pdf(self):
        self.book.published=False;self.book.save()
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(reverse("pdf",args=[self.book.pk])).status_code,404)
        self.assertEqual(self.client.get(reverse("download",args=[self.book.pk])).status_code,404)
    def test_personal_progress_and_favorite(self):
        self.client.force_login(self.student)
        self.client.post(reverse("favorite",args=[self.book.pk]))
        self.client.post(reverse("progress",args=[self.book.pk]),{"page":3})
        r=Reading.objects.get();self.assertTrue(r.favorite);self.assertTrue(r.finished)
        self.assertEqual(r.page,3);self.assertContains(self.client.get(reverse("shelf")),self.book.title)
    def test_review(self):
        self.client.force_login(self.student)
        self.client.post(reverse("review",args=[self.book.pk]),{"rating":5,"comment":"Yaxshi"})
        self.assertEqual(Review.objects.get().rating,5)
    def test_pages(self):
        for name in ["dashboard","catalog","shelf","stats","readers","audit","book_add"]: self.assertEqual(self.client.get(reverse(name)).status_code,200)
        for name in ["read","detail","book_edit"]: self.assertEqual(self.client.get(reverse(name,args=[self.book.pk])).status_code,200)
    def test_search(self):
        self.assertContains(self.client.get(reverse("catalog"),{"q":"Demo"}),"Python")
        self.assertNotContains(self.client.get(reverse("catalog"),{"q":"absent"}),"Python")
    def test_login_required(self):
        self.client.logout();self.assertEqual(self.client.get(reverse("pdf",args=[self.book.pk])).status_code,302)
    def test_username_and_cloud_permissions(self):
        self.student.first_name="Different";self.student.save()
        self.client.force_login(self.student)
        self.assertContains(self.client.get(reverse("dashboard")),"Salom, student!")
        self.assertEqual(self.client.get(reverse("cloud")).status_code,403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("cloud")).status_code,200)
    def test_cloud_storage_routes_new_and_legacy_files(self):
        from unittest.mock import patch
        from django.core.files.base import ContentFile
        from .storage import CloudStorage
        storage=CloudStorage()
        local=storage.save("pdf/local.pdf",ContentFile(b"local"))
        with patch("library.storage.enabled",return_value=True),patch("library.storage.upload",return_value="drive/mockid/new.pdf") as remote:
            name=storage.save("pdf/new.pdf",ContentFile(b"cloud"))
            self.assertEqual(name,"drive/mockid/new.pdf")
            remote.assert_called_once()
            with storage.open(local,"rb") as f:self.assertEqual(f.read(),b"local")
        with patch("library.storage.service") as api:
            api.return_value.files.return_value.get.return_value.execute.return_value={"size":"5"}
            self.assertEqual(storage.size(name),5)
    def test_drive_unavailable_does_not_report_success(self):
        from unittest.mock import patch
        from .storage import DriveUnavailable
        with patch("library.storage.enabled",return_value=True),patch("library.storage.upload",side_effect=DriveUnavailable("Drive unavailable")):
            r=self.client.post(reverse("book_add"),{**self.payload,"title":"Cloud test","pdf":self.valid_pdf()})
            self.assertContains(r,"Drive unavailable")
        self.assertFalse(Book.objects.filter(title="Cloud test").exists())
    def test_audio_upload_play_download_and_filter(self):
        import wave
        buf=BytesIO()
        with wave.open(buf,"wb") as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000);w.writeframes(b"\x00\x00"*8000)
        raw=buf.getvalue()
        response=self.client.post(reverse("book_add"),{**self.payload,"title":"Audio test","audio":SimpleUploadedFile("demo.wav",raw,content_type="audio/wav")})
        self.assertEqual(response.status_code,302, str(response.context["form"].errors) if response.status_code==200 else "")
        audio=Book.objects.get(title="Audio test")
        self.client.force_login(self.student)
        self.assertContains(self.client.get(reverse("catalog"),{"format":"audio"}),"Audio test")
        self.assertNotContains(self.client.get(reverse("catalog"),{"format":"audio"}),"Python")
        self.assertContains(self.client.get(reverse("listen",args=[audio.pk])),"<audio")
        response=self.client.get(reverse("audio_file",args=[audio.pk]),HTTP_RANGE="bytes=0-9")
        self.assertEqual(response.status_code,206);self.assertEqual(b"".join(response.streaming_content),raw[:10])
        response=self.client.get(reverse("audio_file",args=[audio.pk])+"?download=1")
        self.assertIn("attachment",response["Content-Disposition"]);self.assertEqual(b"".join(response.streaming_content),raw)
        audio.published=False;audio.save()
        self.assertEqual(self.client.get(reverse("audio_file",args=[audio.pk])).status_code,404)
