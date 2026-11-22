import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render,redirect,get_object_or_404
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils.crypto import salted_hmac
from .models import Quiz,QuizAttempt,Book
from .views import ctx,guard,staff,visible,audit
from .quiz_engine import parse,generate,ai_available,QuizError

def visible_quizzes(user):
    items=Quiz.objects.select_related("book")
    return items if staff(user) else items.filter(published=True).filter(Q(book__isnull=True)|Q(book__published=True))

@login_required
def index(request):
    items=visible_quizzes(request.user)
    book=request.GET.get("book")
    if book and book.isdigit():items=items.filter(book_id=book)
    return render(request,"library/quizzes.html",ctx(request,quizzes=items,attempts=QuizAttempt.objects.filter(user=request.user).select_related("quiz")[:10]))

@login_required
def edit(request,pk=None):
    guard(request)
    quiz=get_object_or_404(Quiz,pk=pk) if pk else None
    title=quiz.title if quiz else ""
    description=quiz.description if quiz else ""
    book_id=str(quiz.book_id or "") if quiz else request.GET.get("book","")
    source=json.dumps(quiz.questions,ensure_ascii=False,indent=2) if quiz else ""
    error=None
    if request.method=="POST":
        title=request.POST.get("title","").strip()
        description=request.POST.get("description","").strip()
        source=request.POST.get("source","")
        book_id=request.POST.get("book","")
        mode=request.POST.get("action","save")
        try:
            if not title or len(title)>200 or len(description)>2000 or len(source)>60000: raise QuizError("Sarlavha yoki matn uzunligini tekshiring.")
            book=get_object_or_404(Book,pk=book_id) if book_id.isdigit() else None
            if mode=="generate":
                if not request.POST.get("consent"):raise QuizError("Matnni Google Gemini xizmatiga yuborishga rozilik bering.")
                count=int(request.POST.get("count","10"))
                if not 1<=count<=30 or not source.strip():raise QuizError("1–30 savol va manba matnini kiriting.")
                source=json.dumps(generate(source,count,book.title if book else ""),ensure_ascii=False,indent=2)
                messages.success(request,"AI savollar tayyor. Javoblarni tekshiring va qoralama saqlang.")
            else:
                questions=parse(source)
                if quiz is None:quiz=Quiz(created_by=request.user)
                quiz.title=title;quiz.description=description;quiz.book=book;quiz.questions=questions
                quiz.published=False;quiz.save()
                audit(request,"Test qoralamasi saqlandi",quiz)
                messages.success(request,"Qoralama saqlandi. Nashr qilishdan oldin tekshiring.")
                return redirect("quiz_preview",pk=quiz.pk)
        except (QuizError,ValueError) as exc:error=str(exc)
    return render(request,"library/quiz_edit.html",ctx(request,quiz=quiz,title=title,description=description,source=source,book_id=book_id,books=Book.objects.all(),error=error,ai=ai_available()))

@login_required
def preview(request,pk):
    guard(request);quiz=get_object_or_404(Quiz,pk=pk)
    return render(request,"library/quiz_preview.html",ctx(request,quiz=quiz))

@login_required
@require_POST
def publish(request,pk):
    guard(request);quiz=get_object_or_404(Quiz,pk=pk)
    quiz.published=request.POST.get("publish")=="1";quiz.save(update_fields=["published","updated"])
    audit(request,"Test nashr holati o‘zgardi",quiz)
    return redirect("quiz_preview",pk=pk)

def fingerprint(quiz):
    return salted_hmac("quiz-version",json.dumps(quiz.questions,sort_keys=True,ensure_ascii=False)).hexdigest()

@login_required
def take(request,pk):
    quiz=get_object_or_404(visible_quizzes(request.user).filter(published=True),pk=pk)
    if request.method=="POST":
        if fingerprint(quiz)!=request.POST.get("version"):
            messages.error(request,"Test yangilangan. Qayta boshlang.");return redirect("quiz_take",pk=pk)
        result=[];score=0
        for i,q in enumerate(quiz.questions):
            selected=request.POST.get("q"+str(i),"")
            if selected not in {"0","1","2","3"}:
                messages.error(request,"Barcha savollarga javob bering.");break
            chosen=int(selected)
            correct=chosen==q["answer"]
            score+=int(correct)
            result.append(dict(question=q["question"],chosen=q["options"][chosen],correct_answer=q["options"][q["answer"]],correct=correct,explanation=q["explanation"]))
        else:
            attempt=QuizAttempt.objects.create(quiz=quiz,user=request.user,score=score,total=len(result),result=result)
            return redirect("quiz_result",pk=attempt.pk)
    # No answer keys are sent to the test-taking template.
    safe=[dict(question=q["question"],options=list(enumerate(q["options"]))) for q in quiz.questions]
    return render(request,"library/quiz_take.html",ctx(request,quiz=quiz,questions=safe,version=fingerprint(quiz)))

@login_required
def result(request,pk):
    attempt=get_object_or_404(QuizAttempt.objects.select_related("quiz","user"),pk=pk)
    if attempt.user_id!=request.user.id and not staff(request.user):raise PermissionDenied
    return render(request,"library/quiz_result.html",ctx(request,attempt=attempt))

@login_required
def results(request):
    guard(request)
    return render(request,"library/quiz_results.html",ctx(request,attempts=QuizAttempt.objects.select_related("quiz","user")[:200]))
