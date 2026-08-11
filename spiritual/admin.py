from django.contrib import admin
from .models import Category, VideoTrack, SuggestedVideo, UserFavoriteVideo

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(VideoTrack)
class VideoTrackAdmin(admin.ModelAdmin):
    list_display = ('title', 'duration_seconds', 'views_count', 'is_active')
    list_filter = ('is_active', 'categories')
    search_fields = ('title', 'description')

    def delete_model(self, request, obj):
        obj.delete_assets() # Clean Cloudinary
        obj.delete()

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.delete_assets() # Clean Cloudinary
        queryset.delete()

@admin.register(SuggestedVideo)
class SuggestedVideoAdmin(admin.ModelAdmin):
    list_display = ('video', 'priority')

@admin.register(UserFavoriteVideo)
class UserFavoriteVideoAdmin(admin.ModelAdmin):
    list_display = ('user', 'video', 'created_at')
    



