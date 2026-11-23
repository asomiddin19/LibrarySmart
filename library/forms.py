from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from pypdf import PdfReader
from .models import Book,Review,CATEGORIES
from mutagen import File as AudioFile
from zipfile import ZipFile, BadZipFile

class BookForm(forms.ModelForm):
    class Meta:
        model=Book
        fields=["title","author","category","language","year","isbn","description","cover","pdf","epub","audio","published"]
        widgets={"description":forms.Textarea(attrs={"rows":4}),"pdf":forms.FileInput(attrs={"accept":"application/pdf,.pdf"}),"audio":forms.FileInput(attrs={"accept":".mp3,.wav,.m4a,.ogg"})}
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        choices=[(c,c) for c,_ in CATEGORIES]
        if self.instance.category and self.instance.category not in dict(choices): choices.append((self.instance.category,self.instance.category))
        self.fields["category"].widget=forms.Select(choices=choices)
        self.fields["audio"].help_text="MP3, WAV, M4A yoki OGG (150 MB gacha)."
        self.fields["pdf"].help_text="PDF (50 MB gacha)."
        self.fields["epub"].help_text="EPUB (50 MB gacha). PDF, EPUB yoki audio fayldan bittasini tanlang."
    def clean_cover(self):
        f=self.files.get("cover")
        if f:
            if f.size>5*1024*1024 or f.name.rsplit(".",1)[-1].lower() not in {"jpg","jpeg","png","webp"}:
                raise forms.ValidationError("JPG, PNG yoki WEBP, 5 MB gacha.")
            if f.image.format not in {"JPEG","PNG","WEBP"} or f.image.width*f.image.height>16000000:
                raise forms.ValidationError("Muqova formati yoki o‘lchami noto‘g‘ri.")
        return self.cleaned_data.get("cover")
    def clean_audio(self):
        f=self.files.get("audio")
        if not f: return self.cleaned_data.get("audio")
        if f.size>150*1024*1024 or f.name.rsplit(".",1)[-1].lower() not in {"mp3","wav","m4a","ogg"}:
            raise forms.ValidationError("Audio format yoki hajm noto‘g‘ri.")
        try:
            audio=AudioFile(f)
            if audio is None or audio.info is None or audio.info.length<=0: raise ValueError()
        except Exception: raise forms.ValidationError("Audio faylni o‘qib bo‘lmadi.")
        finally: f.seek(0)
        return f
    def clean(self):
        data=super().clean()
        if not data.get("pdf") and not data.get("epub") and not data.get("audio"): raise forms.ValidationError("PDF, EPUB yoki audio kitob yuklang.")
        return data
    def clean_epub(self):
        uploaded = self.files.get("epub")
        if not uploaded:
            return self.cleaned_data.get("epub")
        if uploaded.size > 50 * 1024 * 1024 or not uploaded.name.lower().endswith(".epub"):
            raise forms.ValidationError("Faqat 50 MB gacha EPUB yuklang.")
        try:
            with ZipFile(uploaded) as archive:
                entries = archive.infolist()
                if len(entries) > 5000 or sum(x.file_size for x in entries) > 300 * 1024 * 1024:
                    raise ValueError("Juda katta EPUB arxivi")
                if any(x.filename.startswith("/") or ".." in x.filename.replace("\\\\", "/").split("/") or "\\x00" in x.filename for x in entries):
                    raise ValueError("Noto‘g‘ri EPUB yo‘li")
                if archive.getinfo("mimetype").file_size > 64 or archive.read("mimetype") != b"application/epub+zip":
                    raise ValueError("EPUB mimetype noto‘g‘ri")
                if "META-INF/container.xml" not in archive.namelist():
                    raise ValueError("EPUB tarkibi noto‘g‘ri")
        except (BadZipFile, KeyError, ValueError, RuntimeError, OSError):
            raise forms.ValidationError("EPUB fayli buzilgan yoki noto‘g‘ri.")
        finally:
            uploaded.seek(0)
        return uploaded

    def clean_pdf(self):
        uploaded=self.files.get("pdf")
        if not uploaded: return self.cleaned_data.get("pdf")
        if uploaded.size>50*1024*1024 or not uploaded.name.lower().endswith(".pdf"):
            raise forms.ValidationError("Faqat 50 MB gacha bo‘lgan PDF fayl yuklang.")
        try:
            if uploaded.read(5)!=b"%PDF-": raise ValueError()
            uploaded.seek(0)
            reader=PdfReader(uploaded,strict=False)
            if reader.is_encrypted: raise ValueError()
            self.page_count=len(reader.pages)
            if not 1<=self.page_count<=10000: raise ValueError()
        except Exception:
            raise forms.ValidationError("PDF o‘qib bo‘lmaydi, parollangan yoki buzilgan.")
        finally: uploaded.seek(0)
        return uploaded
    def save(self,commit=True):
        obj=super().save(commit=False)
        if self.files.get("pdf"):
            obj.pages=self.page_count
            obj.file_size=self.files["pdf"].size
        if self.files.get("audio"): obj.audio_size=self.files["audio"].size
        if commit: obj.save()
        return obj

class SignupForm(UserCreationForm):
    first_name=forms.CharField(label="Ism",max_length=150)
    last_name=forms.CharField(label="Familiya",max_length=150)
    email=forms.EmailField(label="Email")
    class Meta:
        model=User
        fields=["username","first_name","last_name","email","password1","password2"]
    def clean_email(self):
        email=self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists(): raise forms.ValidationError("Bu email ro‘yxatdan o‘tgan.")
        return email

class ReviewForm(forms.ModelForm):
    rating=forms.TypedChoiceField(label="Baholash",choices=[(n,f"{n} / 5") for n in range(1,6)],coerce=int)
    class Meta:
        model=Review
        fields=["rating","comment"]
        labels={"comment":"Fikr"}
        widgets={"comment":forms.Textarea(attrs={"rows":3})}
