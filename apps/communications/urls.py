from django.urls import path

from apps.communications.views import InboxView

app_name = 'communications'

urlpatterns = [
    path('', InboxView.as_view(), name='inbox'),
]
