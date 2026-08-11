
# Register your models here.
# user_profiles/admin.py
from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'full_name', 'current_mood_display', 'member_since')
    search_fields = ('user__email', 'full_name')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'