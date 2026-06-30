from django.urls import path

from apps.dojos.views import DojoDetailView, DojoListView

app_name = 'dojos'

urlpatterns = [
    path('', DojoListView.as_view(), name='dojo_list'),
    path('<slug:slug>/', DojoDetailView.as_view(), name='dojo_detail'),
]
