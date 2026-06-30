from django.urls import path

from apps.events.views import EventCreateView, EventDetailView, EventListView

app_name = 'events'

urlpatterns = [
    path('', EventListView.as_view(), name='event_list'),
    path('<int:pk>/', EventDetailView.as_view(), name='event_detail'),
    path('create/', EventCreateView.as_view(), name='event_create'),
]
