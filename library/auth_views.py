import os
from django.contrib.auth.views import LoginView


class LibraryLoginView(LoginView):
    template_name = "registration/login.html"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["google_web_client_id"] = os.getenv("GOOGLE_WEB_CLIENT_ID", "")
        return data
