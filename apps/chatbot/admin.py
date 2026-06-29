from django.contrib import admin
from .models import ChatMessage, ChatSession, FAQEntry


@admin.register(FAQEntry)
class FAQEntryAdmin(admin.ModelAdmin):
    list_display    = ('question_preview', 'category', 'order', 'is_active', 'updated_at')
    list_filter     = ('category', 'is_active')
    search_fields   = ('question', 'answer')
    readonly_fields = ('created_at', 'updated_at')
    actions         = ['action_activate', 'action_deactivate']

    @admin.display(description='Question')
    def question_preview(self, obj):
        return obj.question[:80]

    @admin.action(description='Activate selected FAQ entries')
    def action_activate(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} entry/entries activated.')

    @admin.action(description='Deactivate selected FAQ entries')
    def action_deactivate(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} entry/entries deactivated.')


class ChatMessageInline(admin.TabularInline):
    model           = ChatMessage
    extra           = 0
    readonly_fields = ('role', 'content', 'input_tokens', 'output_tokens', 'created_at')
    can_delete      = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display    = ('session_key', 'member', 'started_at', 'last_active',
                       'is_closed', 'message_count')
    list_filter     = ('is_closed',)
    search_fields   = ('session_key', 'member__member_id', 'member__user__last_name')
    readonly_fields = ('session_key', 'started_at', 'last_active')
    inlines         = [ChatMessageInline]

    def get_queryset(self, request):
        from django.db.models import Count
        return super().get_queryset(request).annotate(_msg_count=Count('messages'))

    @admin.display(description='Messages', ordering='_msg_count')
    def message_count(self, obj):
        return obj._msg_count
