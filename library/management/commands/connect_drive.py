import json,os
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand,CommandError
from library.storage import SCOPES

def private_write(path,data):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,"w") as f: f.write(data)
    os.chmod(path,0o600)

class Command(BaseCommand):
    help="Google Drive OAuth orqali o‘z hisobingizni ulash."
    def add_arguments(self,parser):
        parser.add_argument("--credentials",required=True)
    def handle(self,*args,**opts):
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        if not Path(opts["credentials"]).is_file(): raise CommandError("OAuth credentials.json topilmadi.")
        folder=settings.DRIVE_CONFIG_DIR
        folder.mkdir(mode=0o700,parents=True,exist_ok=True)
        try:
            flow=InstalledAppFlow.from_client_secrets_file(opts["credentials"],SCOPES)
            creds=flow.run_local_server(port=0,access_type="offline",prompt="consent")
            api=build("drive","v3",credentials=creds,cache_discovery=False)
            config_path=folder/"config.json"
            old=json.loads(config_path.read_text()) if config_path.exists() else {}
            if old.get("folder_id"):
                result=api.files().get(fileId=old["folder_id"],fields="id,mimeType,trashed").execute()
                if result.get("trashed") or result["mimeType"]!="application/vnd.google-apps.folder": raise ValueError("Old folder unavailable")
                folder_id=result["id"]
            else:
                result=api.files().create(body={"name":"Library Smart Media","mimeType":"application/vnd.google-apps.folder"},fields="id").execute()
                folder_id=result["id"]
            if not creds.refresh_token: raise ValueError("Missing refresh token")
            private_write(folder/"token.json",creds.to_json())
            private_write(config_path,json.dumps({"folder_id":folder_id}))
        except Exception as exc: raise CommandError("Drive ulanmagan. OAuth sozlamalari va ruxsatni tekshiring.") from exc
        self.stdout.write(self.style.SUCCESS("Google Drive ulandi. Yangi media fayllar avtomatik bulutga saqlanadi."))
