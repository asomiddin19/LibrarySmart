"""Private Drive media storage. Existing local files remain readable."""
import json
import mimetypes
import re
from pathlib import Path
from tempfile import SpooledTemporaryFile
from django.conf import settings
from django.core.files import File
from django.core.files.storage import Storage, FileSystemStorage
from django.core.exceptions import ImproperlyConfigured

SCOPES=["https://www.googleapis.com/auth/drive.file"]
class DriveUnavailable(OSError):
    pass

def enabled():
    return (settings.DRIVE_CONFIG_DIR/"config.json").is_file()

def service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    try:
        credentials=Credentials.from_authorized_user_file(str(settings.DRIVE_CONFIG_DIR/"token.json"),SCOPES)
        if not credentials.valid:
            if not credentials.refresh_token: raise ValueError("No refresh token")
            credentials.refresh(Request())
        return build("drive","v3",credentials=credentials,cache_discovery=False)
    except Exception as exc:
        raise DriveUnavailable("Google Drive ulanmagan yoki ruxsat muddati tugagan.") from exc

def config():
    return json.loads((settings.DRIVE_CONFIG_DIR/"config.json").read_text())

def upload(name,content,folder=None):
    from googleapiclient.http import MediaIoBaseUpload
    content.seek(0)
    filename=Path(name).name
    media=MediaIoBaseUpload(content,mimetype=mimetypes.guess_type(filename)[0] or "application/octet-stream",chunksize=1024*1024,resumable=True)
    try:
        req=service().files().create(body={"name":filename,"parents":[folder or config()["folder_id"]]},media_body=media,fields="id")
        result=None
        while result is None:
            _,result=req.next_chunk(num_retries=3)
        return "drive/"+result["id"]+"/"+filename
    except Exception as exc:
        raise DriveUnavailable("Google Drive faylni saqlay olmadi. Internet va bo‘sh joyni tekshiring.") from exc

def file_id(name):
    parts=name.split("/",2)
    if len(parts)!=3 or parts[0]!="drive" or not re.fullmatch(r"[A-Za-z0-9_-]+",parts[1]):
        raise ValueError("Invalid Drive reference")
    return parts[1]

class CloudStorage(Storage):
    @property
    def local(self):
        return FileSystemStorage(location=settings.MEDIA_ROOT,base_url=settings.MEDIA_URL)
    def _save(self,name,content):
        return upload(name,content) if enabled() else self.local.save(name,content)
    def _open(self,name,mode="rb"):
        if not name.startswith("drive/"): return self.local.open(name,mode)
        if mode!="rb": raise ValueError("Read-only")
        from googleapiclient.http import MediaIoBaseDownload
        buffer=SpooledTemporaryFile(max_size=4*1024*1024,mode="w+b")
        try:
            req=service().files().get_media(fileId=file_id(name))
            downloader=MediaIoBaseDownload(buffer,req,chunksize=1024*1024)
            done=False
            while not done: _,done=downloader.next_chunk(num_retries=3)
            buffer.seek(0)
            return File(buffer,name=Path(name).name)
        except Exception as exc:
            buffer.close()
            raise DriveUnavailable("Google Drive fayli vaqtincha mavjud emas.") from exc
    def exists(self,name):
        if not name.startswith("drive/"): return self.local.exists(name)
        from googleapiclient.errors import HttpError
        try:
            result=service().files().get(fileId=file_id(name),fields="trashed").execute()
            return not result.get("trashed",False)
        except HttpError as exc:
            if exc.resp.status==404:return False
            raise DriveUnavailable("Google Drive tekshiruvida xatolik") from exc
    def size(self,name):
        if not name.startswith("drive/"): return self.local.size(name)
        try: return int(service().files().get(fileId=file_id(name),fields="size").execute()["size"])
        except Exception as exc: raise DriveUnavailable("Google Drive hajmini aniqlab bo‘lmadi.") from exc
    def delete(self,name):
        if not name.startswith("drive/"): return self.local.delete(name)
        # Recoverable deletion, not permanent removal.
        try: service().files().update(fileId=file_id(name),body={"trashed":True}).execute()
        except Exception as exc: raise DriveUnavailable("Google Drive faylini savatga o‘tkazib bo‘lmadi.") from exc
    def url(self,name):
        # Media is served through the authenticated Django views, never public URLs.
        return "#"
