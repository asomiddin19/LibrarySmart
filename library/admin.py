from django.contrib import admin
from .models import Book,Reading,Review,AuditLog,LoginEvent
@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display=("title","author","category","published","pages","reads","downloads")
    search_fields=("title","author")
    list_filter=("published","category","language")
    readonly_fields=("pdf","audio","cover","pages","file_size","audio_size","reads","downloads")
    def has_add_permission(self,request): return False
    def has_delete_permission(self,request,obj=None): return False
admin.site.register(Review)
admin.site.register(Reading)
@admin.register(AuditLog)
class AuditAdmin(admin.ModelAdmin):
    list_display=("actor","action","details","created")
    readonly_fields=("actor","action","details","created")
    def has_add_permission(self,request): return False
    def has_delete_permission(self,request,obj=None): return False

@admin.register(LoginEvent)
class LoginEventAdmin(admin.ModelAdmin):
    list_display = ("created", "user", "email_at_login", "device", "browser")
    list_filter = ("device", "browser", "created")
    search_fields = ("user__username", "user__email", "email_at_login")
    readonly_fields = ("created", "user", "email_at_login", "device", "browser")
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
