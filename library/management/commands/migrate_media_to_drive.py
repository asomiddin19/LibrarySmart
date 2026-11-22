from django.core.management.base import BaseCommand,CommandError
from library.models import Book
from library.storage import enabled,upload
class Command(BaseCommand):
    help="Mahalliy kitob fayllarini Drive'ga nusxalaydi; asl lokal fayllarni o‘chirmaydi."
    def handle(self,*args,**opts):
        if not enabled(): raise CommandError("Avval connect_drive bajaring.")
        count=0
        for book in Book.objects.iterator():
            for name in ("pdf","audio","cover"):
                field=getattr(book,name)
                if not field or field.name.startswith("drive/"):continue
                try:
                    with field.open("rb") as f: new=upload(field.name,f)
                    setattr(book,name,new);book.save(update_fields=[name]);count+=1
                except Exception as exc: raise CommandError(f"Kitob #{book.pk}: ko‘chirish to‘xtadi; lokal fayllar saqlangan.") from exc
        self.stdout.write(self.style.SUCCESS(f"{count} fayl ko‘chirildi. Mahalliy asl nusxalar saqlangan."))
