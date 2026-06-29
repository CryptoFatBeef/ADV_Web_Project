from django.contrib import admin

from .models import ActivityApplication, ActivityEvent, ActivityTemplate


@admin.register(ActivityTemplate)
class ActivityTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'activity_type', 'is_active', 'created_at')
    list_filter = ('activity_type', 'is_active')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ActivityEvent)
class ActivityEventAdmin(admin.ModelAdmin):
    list_display = ('template', 'event', 'dojo', 'scheduled_date')
    list_filter = ('dojo', 'template__activity_type')


def action_submit(modeladmin, request, queryset):
    for obj in queryset.filter(state='DRAFT'):
        obj.submit()
        obj.save()

action_submit.short_description = 'Submit selected applications (DRAFT → Awaiting Coach Rec)'


def action_approve(modeladmin, request, queryset):
    for obj in queryset.filter(state='AWAITING_GM_APPROVAL'):
        obj.approve()
        obj.save()

action_approve.short_description = 'Approve selected applications (Awaiting GM → Pending Payment)'


@admin.register(ActivityApplication)
class ActivityApplicationAdmin(admin.ModelAdmin):
    list_display = ('member', 'activity_event', 'state', 'submitted_at')
    list_filter = ('state', 'activity_event__template__activity_type')
    search_fields = ('member__member_id', 'member__user__last_name')
    readonly_fields = ('state', 'submitted_at', 'completed_at')
    actions = [action_submit, action_approve]
