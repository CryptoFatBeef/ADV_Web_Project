from django.contrib import admin

from .models import SkillRecord


@admin.register(SkillRecord)
class SkillRecordAdmin(admin.ModelAdmin):
    list_display = [
        'member', 'skill_name', 'category', 'result',
        'belt_level_at_assessment', 'assessed_at', 'assessed_by',
    ]
    list_filter = ['category', 'result', 'belt_level_at_assessment']
    search_fields = ['member__member_id', 'member__user__last_name', 'skill_name']

    def get_readonly_fields(self, request, obj=None):
        if obj:  # lock assessed_at after creation
            return ['assessed_at']
        return []
