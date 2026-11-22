from io import BytesIO
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from reportlab.pdfgen import canvas
from library.models import Book
class Command(BaseCommand):
    help="Original demo PDF qo‘llanmalarni yaratish"
    def handle(self,*args,**opts):
        Group.objects.get_or_create(name="Kutubxonachi")
        samples=[
          ("Python: boshlang'ich qo'llanma","Dasturlash",["Python o'zgaruvchilari: qiymatni nom bilan saqlang.","Funksiyalar kodni qayta ishlatishga yordam beradi.","Mashq: sonlar ro'yxati yig'indisini hisoblang."]),
          ("Tarmoq asoslari","Networking",["IP manzil tarmoqdagi qurilmani aniqlaydi.","DNS nomlarni IP manzillarga bog'laydi.","Mashq: uy tarmog'ingiz sxemasini chizing."]),
          ("Linux: amaliy asoslar","Linux",["pwd joriy katalogni ko'rsatadi.","ls katalog mazmunini ro'yxatlaydi.","Mashq: o'z papkangizda fayllarni tartiblang."])]
        for title,category,sections in samples:
            if Book.objects.filter(title=title,author="IT-t 1-jamoa (demo)").exists(): continue
            buf=BytesIO();c=canvas.Canvas(buf)
            for i,section in enumerate(sections,1):
                c.setFont("Helvetica-Bold",18);c.drawString(50,780,title)
                c.setFont("Helvetica",14);c.drawString(50,730,section);c.drawString(50,50,f"IT-t 1-jamoa | Demo | {i}/{len(sections)}");c.showPage()
            c.save();raw=buf.getvalue()
            book=Book(title=title,author="IT-t 1-jamoa (demo)",category=category,description="Namoyish uchun original qisqa PDF qo'llanma.",pages=len(sections),file_size=len(raw))
            book.pdf.save("demo.pdf",ContentFile(raw),save=True)
        self.stdout.write(self.style.SUCCESS("3 ta demo PDF tayyor."))
