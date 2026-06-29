from django.contrib import admin
from django.utils import timezone

from .models import Announcement, ContentBlock


@admin.register(ContentBlock)
class ContentBlockAdmin(admin.ModelAdmin):
    list_display    = ('title', 'section', 'order', 'status', 'is_featured', 'published_at')
    list_filter     = ('section', 'status', 'is_featured')
    search_fields   = ('title',)
    readonly_fields = ('created_at', 'updated_at')
    actions         = ['action_publish', 'action_archive']

    @admin.action(description='Publish selected content blocks')
    def action_publish(self, request, queryset):
        count = queryset.exclude(status='PUBLISHED').update(
            status='PUBLISHED', published_at=timezone.now()
        )
        self.message_user(request, f'{count} block(s) published.')

    @admin.action(description='Archive selected content blocks')
    def action_archive(self, request, queryset):
        count = queryset.exclude(status='ARCHIVED').update(status='ARCHIVED')
        self.message_user(request, f'{count} block(s) archived.')


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display    = ('title', 'status', 'is_pinned', 'published_at', 'expires_at', 'is_active')
    list_filter     = ('status', 'is_pinned')
    search_fields   = ('title',)
    readonly_fields = ('created_at', 'updated_at')
    actions         = ['action_publish']

    @admin.display(description='Active', boolean=True)
    def is_active(self, obj):
        return obj.is_active

    @admin.action(description='Publish selected announcements')
    def action_publish(self, request, queryset):
        count = queryset.exclude(status='PUBLISHED').update(
            status='PUBLISHED', published_at=timezone.now()
        )
        self.message_user(request, f'{count} announcement(s) published.')
