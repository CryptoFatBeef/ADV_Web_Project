from django.urls import path

from apps.matches.views import MatchDetailView, MatchListView

app_name = 'matches'

urlpatterns = [
    path('', MatchListView.as_view(), name='match_list'),
    path('<int:pk>/', MatchDetailView.as_view(), name='match_detail'),
]
