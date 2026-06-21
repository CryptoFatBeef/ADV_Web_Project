from django.contrib import admin

from .models import MemberDojoEnrollment, MemberProfile


class MemberDojoEnrollmentInline(admin.TabularInline):
    model = MemberDojoEnrollment
    extra = 1
    fields = ('dojo', 'enrolled_date', 'is_active')


@admin.register(MemberProfile)
class MemberProfileAdmin(admin.ModelAdmin):
    inlines = [MemberDojoEnrollmentInline]
    list_display = ('member_id', 'full_name', 'current_belt', 'tier', 'status', 'primary_dojo')
    list_filter = ('status', 'tier', 'current_belt', 'primary_dojo')
    search_fields = ('member_id', 'user__first_name', 'user__last_name', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
