from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import ListView

from apps.accounts.mixins import RoleRequiredMixin
from apps.fees.models import AnnualFee, Invoice

ADMIN_ROLES = ['GRANDMASTER', 'DEPUTY_GRANDMASTER', 'ADMIN']


class FeeListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    roles = ADMIN_ROLES
    model = AnnualFee
    template_name = 'fees/fee_list.html'
    context_object_name = 'fees'
    ordering = ['-year']


class InvoicePDFView(LoginRequiredMixin, RoleRequiredMixin, View):
    roles = ADMIN_ROLES

    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        if not invoice.pdf_file:
            invoice.generate_pdf()
        return FileResponse(
            invoice.pdf_file.open('rb'),
            as_attachment=True,
            filename=f'{invoice.invoice_number}.pdf',
        )
