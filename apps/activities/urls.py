from django.urls import path

from apps.activities.views import ActivityDetailView, ActivityListView

app_name = 'activities'

urlpatterns = [
    path('', ActivityListView.as_view(), name='activity_list'),
    path('<int:pk>/', ActivityDetailView.as_view(), name='activity_detail'),
]
