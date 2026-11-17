from django.contrib import admin

from .models import DojoEntity, DojoStaff


class DojoStaffInline(admin.TabularInline):
    model = DojoStaff
    extra = 1
    fields = ('user', 'role', 'coach_level', 'joined_date', 'is_active', 'is_public', 'display_order')


@admin.register(DojoEntity)
class DojoEntityAdmin(admin.ModelAdmin):
    list_display = ('name', 'district', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [DojoStaffInline]


@admin.register(DojoStaff)
class DojoStaffAdmin(admin.ModelAdmin):
    list_display = ('user', 'dojo', 'role', 'coach_level', 'is_active', 'is_public', 'display_order')
    list_filter = ('role', 'coach_level', 'is_active', 'is_public')
    fields = (
        'dojo', 'user', 'role', 'coach_level', 'joined_date', 'is_active',
        'bio_zh', 'bio_en', 'photo', 'certifications',
        'is_public', 'slug', 'display_order',
    )
    readonly_fields = ('slug',)
