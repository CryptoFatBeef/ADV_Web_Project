from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from apps.accounts.mixins import RoleRequiredMixin
from apps.payments.models import PaymentRecord


class PaymentListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    roles = ['GRANDMASTER', 'DEPUTY_GRANDMASTER', 'ADMIN']
    model = PaymentRecord
    template_name = 'payments/payment_list.html'
    context_object_name = 'payments'
    ordering = ['-created_at']
