from django.contrib import admin
from django.db.models import Count

from .models import AttendanceLog, Event


class AttendanceLogInline(admin.TabularInline):
    model = AttendanceLog
    extra = 1
    fields = ('member', 'check_in_method', 'checked_in_at', 'gps_lat', 'gps_lng', 'notes')
    readonly_fields = ('checked_in_at', 'gps_lat', 'gps_lng')


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'event_type', 'status', 'dojo', 'start_datetime', 'attendance_count')
    list_filter = ('event_type', 'status', 'dojo')
    search_fields = ('title',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [AttendanceLogInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _attendance_count=Count('attendancelog')
        )

    @admin.display(description='Attendance')
    def attendance_count(self, obj):
        return obj._attendance_count


@admin.register(AttendanceLog)
class AttendanceLogAdmin(admin.ModelAdmin):
    list_display = ('member', 'event', 'checked_in_at', 'check_in_method')
    search_fields = ('member__member_id', 'member__user__last_name')
    readonly_fields = ('checked_in_at',)
