from django.urls import path

from apps.fees.views import FeeListView, InvoicePDFView

app_name = 'fees'

urlpatterns = [
    path('', FeeListView.as_view(), name='fee_list'),
    path('invoice/<int:pk>/pdf/', InvoicePDFView.as_view(), name='invoice_pdf'),
]
