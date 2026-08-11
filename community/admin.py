from django.contrib import admin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html
from .models import CommunityPost, Like, Comment, Follow, PostReport, DailyPrompt


@admin.register(DailyPrompt)
class DailyPromptAdmin(admin.ModelAdmin):
    list_display = ('text_preview', 'category', 'is_active', 'times_used', 'last_used_at')
    list_filter = ('category', 'is_active')
    search_fields = ('text',)
    readonly_fields = ('times_used', 'last_used_at', 'created_at')

    def text_preview(self, obj):
        return obj.text[:80] + "..." if len(obj.text) > 80 else obj.text
    text_preview.short_description = 'Prompt'

@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display = ('user', 'content_preview', 'created_at', 'likes_count', 'comments_count')
    list_filter = ('created_at',)
    search_fields = ('content',)

    def content_preview(self, obj):
        return obj.content[:50] + "..." if obj.content else ""


@admin.register(PostReport)
class PostReportAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'reported_post_id',
        'post_deleted',
        'post',
        'reporter',
        'reason_preview',
        'delete_post_button',
        'created_at'
    )
    list_filter = ('created_at', 'post_deleted')
    search_fields = ('reason', 'reporter__email', 'post__content')
    actions = ['delete_reported_posts_keep_reports']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:report_id>/delete-reported-post/',
                self.admin_site.admin_view(self.delete_reported_post_view),
                name='community_postreport_delete_reported_post',
            ),
        ]
        return custom_urls + urls

    def delete_post_button(self, obj):
        if obj.post_deleted or not obj.post:
            return "Post deleted"

        url = reverse('admin:community_postreport_delete_reported_post', args=[obj.id])
        return format_html('<a class="button" href="{}">Delete Post</a>', url)

    delete_post_button.short_description = 'Moderation Action'

    def _delete_post_keep_report(self, report):
        if report.post:
            report.post.delete()
            report.post = None
            report.post_deleted = True
            report.save(update_fields=['post', 'post_deleted'])
            return True

        report.post_deleted = True
        report.save(update_fields=['post_deleted'])
        return False

    def delete_reported_post_view(self, request, report_id):
        report = self.get_object(request, report_id)
        if report is None:
            self.message_user(request, "Report not found.", level=messages.ERROR)
            return HttpResponseRedirect(reverse('admin:community_postreport_changelist'))

        deleted = self._delete_post_keep_report(report)
        if deleted:
            self.message_user(request, "Reported post deleted. Report record kept.", level=messages.SUCCESS)
        else:
            self.message_user(request, "Post was already deleted. Report record kept.", level=messages.INFO)

        return HttpResponseRedirect(reverse('admin:community_postreport_changelist'))

    def reason_preview(self, obj):
        return obj.reason[:80] + "..." if len(obj.reason) > 80 else obj.reason

    def delete_model(self, request, obj):
        if self._delete_post_keep_report(obj):
            self.message_user(request, "Reported post deleted. Report record kept.", level=messages.SUCCESS)
            return

        self.message_user(request, "Post was already deleted. Report record kept.", level=messages.INFO)

    def delete_queryset(self, request, queryset):
        deleted_count = 0
        for report in queryset:
            if self._delete_post_keep_report(report):
                deleted_count += 1

        self.message_user(
            request,
            f"Deleted {deleted_count} reported post(s). Report record(s) kept.",
            level=messages.SUCCESS
        )

    @admin.action(description='Delete reported post (keep report)')
    def delete_reported_posts_keep_reports(self, request, queryset):
        deleted_count = 0
        for report in queryset:
            if self._delete_post_keep_report(report):
                deleted_count += 1

        self.message_user(
            request,
            f"Deleted {deleted_count} reported post(s). Report record(s) kept.",
            level=messages.SUCCESS
        )