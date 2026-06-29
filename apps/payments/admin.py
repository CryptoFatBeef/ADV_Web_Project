from django.contrib import admin
from django.utils import timezone

from .models import FPSQRCode, PaymentRecord, PaymentStatus


class FPSQRCodeInline(admin.StackedInline):
    model = FPSQRCode
    extra = 0
    readonly_fields = ('qr_image', 'generated_at')


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'annual_fee', 'method', 'status',
        'amount', 'currency', 'get_confirmed_by', 'created_at',
    )
    list_filter = ('status', 'method', 'currency')
    search_fields = (
        'annual_fee__member__member_id',
        'annual_fee__member__user__last_name',
        'reference_id',
    )
    readonly_fields = ('email_matched_at', 'confirmed_at', 'created_at', 'updated_at')
    inlines = [FPSQRCodeInline]
    actions = ['action_manually_confirm']

    @admin.display(description='Confirmed By')
    def get_confirmed_by(self, obj):
        return obj.confirmed_by or '—'

    @admin.action(description='Manually confirm selected payments')
    def action_manually_confirm(self, request, queryset):
        confirmable = queryset.filter(
            status__in=[PaymentStatus.SCREENSHOT_UPLOADED, PaymentStatus.EMAIL_MATCHED]
        )
        count = confirmable.update(
            status=PaymentStatus.MANUALLY_CONFIRMED,
            confirmed_by_id=request.user.pk,
            confirmed_at=timezone.now(),
        )
        self.message_user(request, f'{count} payment(s) marked as manually confirmed.')


@admin.register(FPSQRCode)
class FPSQRCodeAdmin(admin.ModelAdmin):
    list_display = ('payment_record', 'merchant_name', 'fps_id', 'amount', 'generated_at', 'expires_at')
    readonly_fields = ('qr_image', 'generated_at')
    search_fields = ('payment_record__annual_fee__member__member_id', 'fps_id')
