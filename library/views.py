from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User,Group
from django.core.exceptions import PermissionDenied
from django.db.models import Avg,Count,Q,Sum,F
from django.http import FileResponse,Http404,StreamingHttpResponse,HttpResponse
import re
from django.shortcuts import render,redirect,get_object_or_404
from django.views.decorators.http import require_POST
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.db import transaction
from django.core.paginator import Paginator
from .models import Book,Reading,Review,AuditLog,CATEGORIES,LoginEvent
from .forms import BookForm,SignupForm,ReviewForm
from .storage import enabled,service,DriveUnavailable

def staff(user): return user.is_authenticated and (user.is_superuser or user.groups.filter(name="Kutubxonachi").exists())
def guard(request):
    if not staff(request.user): raise PermissionDenied
def audit(request,action,details): AuditLog.objects.create(actor=request.user,action=action,details=str(details)[:250])
def ctx(request,**kw): return {"can_manage":staff(request.user),"is_admin":request.user.is_superuser,**kw}
def visible(user): return Book.objects.all() if staff(user) else Book.objects.filter(published=True)
def metrics(user):
    books=visible(user)
    sums=books.aggregate(reads=Sum("reads"),downloads=Sum("downloads"))
    return dict(total=books.count(),reads=sums["reads"] or 0,downloads=sums["downloads"] or 0,categories=books.order_by().values("category").distinct().count())
@login_required
def dashboard(request):
    recent=Reading.objects.filter(user=request.user,book__in=visible(request.user)).select_related("book")[:4]
    counts={r["category"]:r["n"] for r in visible(request.user).values("category").annotate(n=Count("id"))}
    categories=[(name,icon,counts.get(name,0)) for name,icon in CATEGORIES]
    return render(request,"library/dashboard.html",ctx(request,metrics=metrics(request.user),books=visible(request.user)[:6],recent=recent,categories=categories,audio_books=visible(request.user).exclude(audio="")[:6],popular=visible(request.user).order_by("-reads")[:3]))
@login_required
def catalog(request):
    q=request.GET.get("q","").strip(); category=request.GET.get("category",""); sort=request.GET.get("sort","new")
    all_books=visible(request.user)
    books=all_books.annotate(rating=Avg("reviews__rating"))
    if q: books=books.filter(Q(title__icontains=q)|Q(author__icontains=q)|Q(category__icontains=q)|Q(isbn__icontains=q)|Q(description__icontains=q))
    if category: books=books.filter(category=category)
    mode=request.GET.get("format","all")
    if mode=="audio": books=books.exclude(audio="")
    elif mode=="pdf": books=books.exclude(pdf="")
    elif mode=="epub": books=books.exclude(epub="")
    books=books.order_by({"popular":"-reads","title":"title","rating":"-rating"}.get(sort,"-created"))
    page=Paginator(books,18).get_page(request.GET.get("page"))
    return render(request,"library/catalog.html",ctx(request,books=page,page=page,query=q,category=category,sort=sort,mode=mode,categories=all_books.order_by("category").values_list("category",flat=True).distinct()))
@login_required
def detail(request,pk):
    book=get_object_or_404(visible(request.user),pk=pk)
    reading=Reading.objects.filter(user=request.user,book=book).first()
    review=Review.objects.filter(user=request.user,book=book).first()
    return render(request,"library/detail.html",ctx(request,book=book,reading=reading,reviews=book.reviews.select_related("user"),rating=book.reviews.aggregate(n=Avg("rating"))["n"],form=ReviewForm(instance=review)))
@login_required
def book_edit(request,pk=None):
    guard(request)
    book=get_object_or_404(Book,pk=pk) if pk else None
    if request.method=="POST":
        form=BookForm(request.POST,request.FILES,instance=book)
        if form.is_valid():
            old=Book.objects.get(pk=pk) if pk else None
            old_pdf=old.pdf.name if old else None
            try:
                with transaction.atomic(): saved=form.save()
            except DriveUnavailable as exc:
                form.add_error(None,str(exc))
                return render(request,"library/form.html",ctx(request,form=form,title="Kitobni saqlash"))
            if old and old.epub and old.epub.name != saved.epub.name:
                transaction.on_commit(lambda: old.epub.storage.delete(old.epub.name))
            if old_pdf and old_pdf!=saved.pdf.name:
                transaction.on_commit(lambda: saved.pdf.storage.delete(old_pdf))
                Reading.objects.filter(book=saved,page__gt=saved.pages).update(page=saved.pages,finished=False)
            if old and old.audio and old.audio.name!=saved.audio.name:
                transaction.on_commit(lambda:old.audio.storage.delete(old.audio.name))
            if old and old.cover and old.cover.name!=saved.cover.name:
                transaction.on_commit(lambda:old.cover.storage.delete(old.cover.name))
            audit(request,"Elektron kitob saqlandi",saved);messages.success(request,"Kitob saqlandi.");return redirect("detail",pk=saved.pk)
    else: form=BookForm(instance=book)
    return render(request,"library/form.html",ctx(request,form=form,title="Kitobni tahrirlash" if pk else "Yangi PDF kitob"))
@login_required
@require_POST
def book_delete(request,pk):
    guard(request);book=get_object_or_404(Book,pk=pk)
    storage,name=book.pdf.storage,book.pdf.name
    with transaction.atomic():
        audit(request,"Kitob o‘chirildi",book);book.delete()
        if name: transaction.on_commit(lambda:storage.delete(name))
        if book.epub: transaction.on_commit(lambda:book.epub.storage.delete(book.epub.name))
        if book.audio: transaction.on_commit(lambda:book.audio.storage.delete(book.audio.name))
        if book.cover: transaction.on_commit(lambda:book.cover.storage.delete(book.cover.name))
    messages.success(request,"Kitob o‘chirildi.");return redirect("catalog")
@login_required
def read(request,pk):
    book=get_object_or_404(visible(request.user),pk=pk)
    if not book.pdf:
        if book.epub:
            reading,_=Reading.objects.get_or_create(book=book,user=request.user)
            Book.objects.filter(pk=pk).update(reads=F("reads")+1)
            return render(request,"library/read_epub.html",ctx(request,book=book,reading=reading))
        return redirect("listen",pk=pk)
    reading,_=Reading.objects.get_or_create(book=book,user=request.user)
    Book.objects.filter(pk=pk).update(reads=F("reads")+1)
    return render(request,"library/read.html",ctx(request,book=book,reading=reading))
def pdf_response(request,pk,attachment):
    book=get_object_or_404(visible(request.user).exclude(pdf=""),pk=pk)
    try: file=book.pdf.open("rb")
    except DriveUnavailable: return HttpResponse("Google Drive vaqtincha mavjud emas.",status=503)
    except (FileNotFoundError,ValueError): raise Http404("PDF topilmadi")
    if attachment: Book.objects.filter(pk=pk).update(downloads=F("downloads")+1)
    response=FileResponse(file,content_type="application/pdf",as_attachment=attachment,filename=f"{book.title}.pdf")
    response["Cache-Control"]="private, no-store"
    return response
def epub_response(request,pk):
    book=get_object_or_404(visible(request.user).exclude(epub=""),pk=pk)
    try: file=book.epub.open("rb")
    except DriveUnavailable: return HttpResponse("Google Drive vaqtincha mavjud emas.",status=503)
    except (FileNotFoundError,ValueError): raise Http404("EPUB topilmadi")
    response=FileResponse(file,content_type="application/epub+zip",filename=f"{book.title}.epub")
    response["Cache-Control"]="private, no-store"
    response["X-Content-Type-Options"]="nosniff"
    return response

@login_required
def epub(request,pk): return epub_response(request,pk)

@login_required
@xframe_options_sameorigin
def pdf(request,pk): return pdf_response(request,pk,False)
@login_required
def download(request,pk): return pdf_response(request,pk,True)
@login_required
def cover_file(request,pk):
    book=get_object_or_404(visible(request.user).exclude(cover=""),pk=pk)
    try: f=book.cover.open("rb")
    except DriveUnavailable: return HttpResponse("Google Drive vaqtincha mavjud emas.",status=503)
    except (ValueError,FileNotFoundError): raise Http404()
    from PIL import Image
    try:
        with Image.open(f) as image: mime=Image.MIME[image.format]
        f.seek(0)
    except Exception:
        f.close();raise Http404()
    return FileResponse(f,content_type=mime,headers={"Cache-Control":"private, no-store"})
@login_required
def listen(request,pk):
    book=get_object_or_404(visible(request.user).exclude(audio=""),pk=pk)
    Reading.objects.get_or_create(user=request.user,book=book)
    Book.objects.filter(pk=pk).update(reads=F("reads")+1)
    return render(request,"library/listen.html",ctx(request,book=book))
@login_required
def audio_file(request,pk):
    book=get_object_or_404(visible(request.user).exclude(audio=""),pk=pk)
    try: f=book.audio.open("rb")
    except DriveUnavailable: return HttpResponse("Google Drive vaqtincha mavjud emas.",status=503)
    except (ValueError,FileNotFoundError): raise Http404()
    suffix=book.audio.name.rsplit(".",1)[-1]
    mime={"mp3":"audio/mpeg","wav":"audio/wav","m4a":"audio/mp4","ogg":"audio/ogg"}[suffix]
    attachment=request.GET.get("download")=="1"
    if attachment: Book.objects.filter(pk=pk).update(downloads=F("downloads")+1)
    # Byte-range support allows native audio players to seek without downloading the entire book.
    length=book.audio_size or book.audio.size
    range_header=request.headers.get("Range")
    if range_header and not attachment:
        match=re.fullmatch(r"bytes=(\d*)-(\d*)",range_header)
        start=end=None
        if match and (match[1] or match[2]):
            if match[1]:
                start=int(match[1]);end=min(int(match[2]),length-1) if match[2] else length-1
            else:
                start=max(0,length-int(match[2]));end=length-1
        if start is None or start>=length or end<start:
            f.close()
            return HttpResponse(status=416,headers={"Content-Range":f"bytes */{length}","Accept-Ranges":"bytes"})
        def chunks():
            try:
                f.seek(start);remaining=end-start+1
                while remaining:
                    chunk=f.read(min(65536,remaining))
                    if not chunk: break
                    remaining-=len(chunk);yield chunk
            finally: f.close()
        return StreamingHttpResponse(chunks(),status=206,content_type=mime,headers={"Content-Range":f"bytes {start}-{end}/{length}","Content-Length":str(end-start+1),"Accept-Ranges":"bytes","Cache-Control":"private, no-store"})
    response=FileResponse(f,content_type=mime,as_attachment=attachment,filename=f"{book.title}.{suffix}")
    response["Cache-Control"]="private, no-store"
    response["Accept-Ranges"]="bytes"
    return response
@login_required
@require_POST
def favorite(request,pk):
    book=get_object_or_404(visible(request.user),pk=pk)
    reading,_=Reading.objects.get_or_create(user=request.user,book=book)
    reading.favorite=not reading.favorite;reading.save()
    return redirect("detail",pk=pk)
@login_required
@require_POST
def progress(request,pk):
    book=get_object_or_404(visible(request.user),pk=pk)
    try: page=int(request.POST.get("page",""))
    except ValueError: page=0
    if 1<=page<=book.pages:
        Reading.objects.update_or_create(user=request.user,book=book,defaults={"page":page,"finished":page==book.pages})
        messages.success(request,"O‘qish sahifasi saqlandi.")
    else: messages.error(request,"Sahifa raqami noto‘g‘ri.")
    return redirect("read",pk=pk)
@login_required
@require_POST
def review(request,pk):
    book=get_object_or_404(visible(request.user),pk=pk)
    instance=Review.objects.filter(user=request.user,book=book).first()
    form=ReviewForm(request.POST,instance=instance)
    if form.is_valid():
        obj=form.save(commit=False);obj.user=request.user;obj.book=book;obj.save()
        messages.success(request,"Fikringiz saqlandi.")
    else: messages.error(request,"Bahoni va fikrni tekshiring.")
    return redirect("detail",pk=pk)
@login_required
def shelf(request):
    readings=Reading.objects.filter(user=request.user,book__in=visible(request.user)).select_related("book")
    mode=request.GET.get("mode","all")
    if mode=="favorite": readings=readings.filter(favorite=True)
    elif mode=="finished": readings=readings.filter(finished=True)
    return render(request,"library/shelf.html",ctx(request,readings=readings,mode=mode))
def signup(request):
    if request.user.is_authenticated and not staff(request.user): return redirect("dashboard")
    form=SignupForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        user=form.save()
        if request.user.is_authenticated:
            audit(request,"Kitobxon yaratildi",user);return redirect("readers")
        messages.success(request,"Hisob yaratildi. Endi kiring.");return redirect("login")
    return render(request,"library/form.html",ctx(request,form=form,title="Ro‘yxatdan o‘tish"))
@login_required
def readers(request):
    guard(request)
    readers_qs = User.objects.order_by("username").prefetch_related("groups")
    recent_logins = LoginEvent.objects.select_related("user").order_by("-created")[:100]
    return render(request,"library/readers.html",ctx(request,readers=readers_qs,recent_logins=recent_logins))
@login_required
@require_POST
def set_role(request,pk):
    if not request.user.is_superuser: raise PermissionDenied
    user=get_object_or_404(User,pk=pk)
    if user.is_superuser: raise PermissionDenied
    group,_=Group.objects.get_or_create(name="Kutubxonachi")
    if request.POST.get("role")=="librarian": user.groups.add(group)
    elif request.POST.get("role")=="student": user.groups.remove(group)
    else: raise PermissionDenied
    audit(request,"Rol o‘zgartirildi",user);messages.success(request,"Rol saqlandi.");return redirect("readers")
@login_required
def stats(request):
    books=visible(request.user)
    return render(request,"library/stats.html",ctx(request,metrics=metrics(request.user),categories=books.values("category").annotate(n=Count("id")).order_by("-n"),popular=books.order_by("-reads")[:10]))
@login_required
def history(request):
    if not request.user.is_superuser: raise PermissionDenied
    return render(request,"library/audit.html",ctx(request,logs=AuditLog.objects.select_related("actor")[:200]))
@login_required
def cloud_status(request):
    if not request.user.is_superuser: raise PermissionDenied
    connected=enabled(); quota=None; error=None
    if connected:
        try:
            info=service().about().get(fields="storageQuota").execute()["storageQuota"]
            used=int(info.get("usage",0));limit=int(info.get("limit",0))
            quota={"used":round(used/1e9,2),"limit":round(limit/1e9,2),"free":round(max(0,limit-used)/1e9,2),"percent":min(100,round(used/max(1,limit)*100))}
        except Exception: error="Google Drive bilan bog‘lanib bo‘lmadi. OAuth ruxsatini tekshiring."
    return render(request,"library/cloud.html",ctx(request,connected=connected,quota=quota,error=error))
