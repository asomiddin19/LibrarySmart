import sqlite3
from tempfile import TemporaryDirectory
from pathlib import Path
from datetime import datetime,timezone
from django.conf import settings
from django.core.management.base import BaseCommand,CommandError
from library.storage import enabled,upload
class Command(BaseCommand):
    help="SQLite bazasi nusxasini Google Drive'ga xavfsiz yuboradi."
    def handle(self,*args,**opts):
        if not enabled(): raise CommandError("Avval Drive'ni ulang.")
        db=settings.DATABASES["default"]
        if db["ENGINE"]!="django.db.backends.sqlite3": raise CommandError("Bu buyruq faqat SQLite uchun.")
        with TemporaryDirectory() as tmp:
            name="library-backup-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")+".sqlite3"
            path=Path(tmp)/name
            try:
                source=sqlite3.connect(str(db["NAME"]));target=sqlite3.connect(path)
                try:source.backup(target)
                finally:target.close();source.close()
                with path.open("rb") as f:upload(name,f)
            except Exception as exc:raise CommandError("Zaxiralash bajarilmadi.") from exc
        self.stdout.write(self.style.SUCCESS("SQLite zaxirasi Drive'ga saqlandi."))
