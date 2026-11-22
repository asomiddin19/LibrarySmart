from django.urls import path
from . import views,quiz_views
urlpatterns=[
 path("",views.dashboard,name="dashboard"),path("books/",views.catalog,name="catalog"),
 path("tests/",quiz_views.index,name="quizzes"),path("tests/new/",quiz_views.edit,name="quiz_new"),path("tests/results/",quiz_views.results,name="quiz_results"),
 path("tests/<int:pk>/edit/",quiz_views.edit,name="quiz_edit"),path("tests/<int:pk>/preview/",quiz_views.preview,name="quiz_preview"),path("tests/<int:pk>/publish/",quiz_views.publish,name="quiz_publish"),path("tests/<int:pk>/take/",quiz_views.take,name="quiz_take"),path("tests/result/<int:pk>/",quiz_views.result,name="quiz_result"),
 path("books/add/",views.book_edit,name="book_add"),path("books/<int:pk>/",views.detail,name="detail"),
 path("books/<int:pk>/edit/",views.book_edit,name="book_edit"),path("books/<int:pk>/delete/",views.book_delete,name="book_delete"),
 path("books/<int:pk>/read/",views.read,name="read"),path("books/<int:pk>/pdf/",views.pdf,name="pdf"),path("books/<int:pk>/download/",views.download,name="download"),
 path("books/<int:pk>/favorite/",views.favorite,name="favorite"),path("books/<int:pk>/progress/",views.progress,name="progress"),path("books/<int:pk>/review/",views.review,name="review"),
 path("books/<int:pk>/listen/",views.listen,name="listen"),path("books/<int:pk>/audio/",views.audio_file,name="audio_file"),path("books/<int:pk>/cover/",views.cover_file,name="cover_file"),
 path("shelf/",views.shelf,name="shelf"),path("signup/",views.signup,name="signup"),path("readers/",views.readers,name="readers"),path("readers/<int:pk>/role/",views.set_role,name="set_role"),path("stats/",views.stats,name="stats"),path("audit/",views.history,name="audit"),path("cloud/",views.cloud_status,name="cloud")]
