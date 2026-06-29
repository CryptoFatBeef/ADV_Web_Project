from django.contrib import admin

from .models import AnnualFee, Invoice


class InvoiceInline(admin.StackedInline):
    model = Invoice
    extra = 0
    readonly_fields = ('invoice_number', 'issued_at', 'pdf_file')


@admin.register(AnnualFee)
class AnnualFeeAdmin(admin.ModelAdmin):
    list_display = (
        'member', 'year', 'tier_at_billing',
        'amount_due', 'amount_paid', 'get_balance_due',
        'status', 'due_date',
    )
    list_filter = ('status', 'year', 'tier_at_billing')
    search_fields = ('member__member_id', 'member__user__last_name')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [InvoiceInline]

    @admin.display(description='Balance Due (HK$)')
    def get_balance_due(self, obj):
        return obj.balance_due


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'annual_fee', 'issued_at', 'pdf_file')
    search_fields = ('invoice_number', 'annual_fee__member__member_id')
    readonly_fields = ('invoice_number', 'issued_at')
    actions = ['action_generate_pdf']

    @admin.action(description='Generate PDF for selected invoices')
    def action_generate_pdf(self, request, queryset):
        for invoice in queryset:
            invoice.generate_pdf()
