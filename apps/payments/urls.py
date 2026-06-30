from django.urls import path

from apps.payments.views import PaymentListView

app_name = 'payments'

urlpatterns = [
    path('', PaymentListView.as_view(), name='payment_list'),
]
