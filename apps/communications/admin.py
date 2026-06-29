from django.contrib import admin

from .models import Notification, NotificationTemplate


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'channel', 'is_active', 'created_at')
    list_filter = ('channel', 'is_active')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'channel', 'status', 'sent_at', 'created_at')
    list_filter = ('channel', 'status')
    search_fields = ('recipient__member_id', 'recipient__user__last_name')
    readonly_fields = ('body', 'sent_at', 'read_at', 'failure_reason', 'created_at')
    actions = ['action_retry_failed']

    @admin.action(description='Retry failed notifications')
    def action_retry_failed(self, request, queryset):
        from apps.communications.services import send_notification
        count = 0
        for n in queryset.filter(status='FAILED'):
            n.status = 'PENDING'
            n.failure_reason = ''
            send_notification(n)
            n.save(update_fields=['status', 'sent_at', 'failure_reason'])
            count += 1
        self.message_user(request, f'{count} notification(s) retried.')
