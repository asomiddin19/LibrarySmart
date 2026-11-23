from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator,MaxValueValidator
from uuid import uuid4

def pdf_path(instance,filename):
    return f"pdf/{uuid4().hex}.pdf"
def epub_path(instance, filename):
    return f"epub/{uuid4().hex}.epub"

def audio_path(instance,filename):
    return f"audio/{uuid4().hex}.{filename.rsplit('.',1)[-1].lower()}"
def cover_path(instance,filename):
    return f"covers/{uuid4().hex}.{filename.rsplit('.',1)[-1].lower()}"

CATEGORIES=[
 ("Badiiy adabiyot","📚"),("O‘zbek adabiyoti","🌿"),("Jahon adabiyoti","🌍"),
 ("Dasturlash","💻"),("Networking","🌐"),("Linux","🐧"),("Kiberxavfsizlik","🛡️"),
 ("Sun’iy intellekt","🤖"),("Matematika","∑"),("Fizika","⚛️"),("Tarix","🏛️"),
 ("Psixologiya","🧠"),("Biznes va iqtisod","📈"),("Tillar","🗣️"),
 ("Tibbiyot","🩺"),("Bolalar adabiyoti","🧸"),("Ilm-fan","🔬"),("Shaxsiy rivojlanish","✨")
]

class Book(models.Model):
    title=models.CharField("Kitob nomi",max_length=200)
    author=models.CharField("Muallif",max_length=180)
    category=models.CharField("Kategoriya",max_length=100)
    language=models.CharField("Til",max_length=60,default="O‘zbek")
    year=models.PositiveIntegerField("Nashr yili",null=True,blank=True)
    isbn=models.CharField("ISBN",max_length=40,blank=True)
    description=models.TextField("Tavsif")
    pdf=models.FileField("PDF fayl",upload_to=pdf_path,blank=True)
    epub=models.FileField("EPUB fayl",upload_to=epub_path,blank=True)
    audio=models.FileField("Audio kitob",upload_to=audio_path,blank=True)
    audio_size=models.PositiveBigIntegerField(default=0)
    cover=models.ImageField("Kitob muqovasi",upload_to=cover_path,blank=True)
    pages=models.PositiveIntegerField(default=1)
    file_size=models.PositiveBigIntegerField(default=0)
    published=models.BooleanField("Katalogda ko‘rsatish",default=True)
    downloads=models.PositiveBigIntegerField(default=0)
    reads=models.PositiveBigIntegerField(default=0)
    created=models.DateTimeField(auto_now_add=True)
    updated=models.DateTimeField(auto_now=True)
    class Meta: ordering=["-created"]
    def __str__(self): return self.title
    @property
    def size_mb(self): return round(self.file_size/1024/1024,2)
    @property
    def audio_mb(self): return round(self.audio_size/1024/1024,2)

class Reading(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name="readings")
    book=models.ForeignKey(Book,on_delete=models.CASCADE,related_name="readings")
    favorite=models.BooleanField(default=False)
    page=models.PositiveIntegerField(default=1)
    locator=models.CharField(max_length=1024, blank=True)
    finished=models.BooleanField(default=False)
    updated=models.DateTimeField(auto_now=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=["user","book"],name="unique_reading")]
        ordering=["-updated"]
    @property
    def percent(self): return min(100,round(self.page/max(1,self.book.pages)*100))

class Review(models.Model):
    book=models.ForeignKey(Book,on_delete=models.CASCADE,related_name="reviews")
    user=models.ForeignKey(User,on_delete=models.CASCADE)
    rating=models.PositiveSmallIntegerField(validators=[MinValueValidator(1),MaxValueValidator(5)])
    comment=models.CharField(max_length=1000,blank=True)
    updated=models.DateTimeField(auto_now=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=["user","book"],name="unique_review")]
        ordering=["-updated"]

class AuditLog(models.Model):
    actor=models.ForeignKey(User,on_delete=models.SET_NULL,null=True)
    action=models.CharField(max_length=100)
    details=models.CharField(max_length=250)
    created=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=["-created"]

class Quiz(models.Model):
    book=models.ForeignKey(Book,on_delete=models.CASCADE,related_name="quizzes",null=True,blank=True)
    title=models.CharField(max_length=200)
    description=models.TextField(blank=True)
    questions=models.JSONField(default=list)
    published=models.BooleanField(default=False)
    created_by=models.ForeignKey(User,on_delete=models.SET_NULL,null=True)
    created=models.DateTimeField(auto_now_add=True)
    updated=models.DateTimeField(auto_now=True)
    class Meta: ordering=["-created"]
    def __str__(self):return self.title

class QuizAttempt(models.Model):
    quiz=models.ForeignKey(Quiz,on_delete=models.CASCADE,related_name="attempts")
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name="quiz_attempts")
    score=models.PositiveIntegerField()
    total=models.PositiveIntegerField()
    result=models.JSONField(default=list)
    created=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=["-created"]
    @property
    def percent(self): return round(100*self.score/max(1,self.total))


class GoogleIdentity(models.Model):
    """Verified OIDC subject is the stable identity, not a mutable email or username."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="google_identity")
    subject = models.CharField(max_length=128, unique=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Google identity for user {self.user_id}"



class AIMessage(models.Model):
    """A user's saved book Q&A history across web and mobile."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ai_messages")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="ai_messages")
    question = models.CharField(max_length=800)
    answer = models.TextField(max_length=12000)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"AI message {self.pk} for user {self.user_id}"
