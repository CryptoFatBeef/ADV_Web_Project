from django.contrib import admin

from .models import (
    BeltPromotionRecord,
    MemberCertificate,
    MemberDojoEnrollment,
    MemberGuardian,
    MemberProfile,
    RegistrationInvitation,
)


class MemberDojoEnrollmentInline(admin.TabularInline):
    model = MemberDojoEnrollment
    extra = 1
    fields = ('dojo', 'enrolled_date', 'is_active')


class BeltPromotionRecordInline(admin.TabularInline):
    model = BeltPromotionRecord
    extra = 1
    fields = ('belt', 'promoted_date', 'dojo', 'promoted_by', 'notes')


class MemberCertificateInline(admin.TabularInline):
    model = MemberCertificate
    extra = 1
    fields = ('certificate_name', 'issuing_body', 'date_acquired', 'valid_until', 'certificate_number', 'notes')


class MemberGuardianInline(admin.TabularInline):
    model = MemberGuardian
    extra = 1
    fields = ('guardian', 'relationship', 'is_primary')


@admin.register(MemberProfile)
class MemberProfileAdmin(admin.ModelAdmin):
    inlines = [MemberDojoEnrollmentInline, MemberGuardianInline, BeltPromotionRecordInline, MemberCertificateInline]
    list_display = ('member_id', 'full_name', 'chinese_name', 'current_belt', 'tier', 'status', 'primary_dojo')
    list_filter = ('status', 'tier', 'current_belt', 'primary_dojo')
    search_fields = ('member_id', 'chinese_name', 'user__first_name', 'user__last_name', 'user__email')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(BeltPromotionRecord)
class BeltPromotionRecordAdmin(admin.ModelAdmin):
    list_display = ('member', 'belt', 'promoted_date', 'dojo', 'promoted_by')
    list_filter = ('belt', 'dojo')
    search_fields = ('member__member_id', 'member__user__last_name')


@admin.register(MemberCertificate)
class MemberCertificateAdmin(admin.ModelAdmin):
    list_display = ('member', 'certificate_name', 'issuing_body', 'date_acquired', 'valid_until')
    list_filter = ('issuing_body',)
    search_fields = ('member__member_id', 'member__user__last_name', 'certificate_name')


@admin.register(MemberGuardian)
class MemberGuardianAdmin(admin.ModelAdmin):
    list_display = ('member', 'guardian', 'relationship', 'is_primary')
    list_filter = ('relationship', 'is_primary')
    search_fields = ('member__member_id', 'member__user__last_name', 'guardian__email', 'guardian__last_name')


@admin.register(RegistrationInvitation)
class RegistrationInvitationAdmin(admin.ModelAdmin):
    list_display = ('contact_email', 'target_dojo', 'status', 'created_by', 'created_at', 'expires_at')
    list_filter = ('status', 'target_dojo')
    search_fields = ('contact_email',)
    readonly_fields = ('token', 'created_at')
