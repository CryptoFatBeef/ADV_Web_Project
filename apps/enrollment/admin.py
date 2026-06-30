from django.contrib import admin

from .models import EnrollmentLead


@admin.register(EnrollmentLead)
class EnrollmentLeadAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'contact_phone', 'interested_dojo', 'status', 'created_at')
    list_filter = ('status', 'interested_dojo')
    search_fields = ('full_name', 'contact_phone', 'contact_email')
