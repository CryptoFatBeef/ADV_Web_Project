from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, ListView

from apps.matches.models import Tournament


class MatchListView(LoginRequiredMixin, ListView):
    model = Tournament
    template_name = 'matches/match_list.html'
    context_object_name = 'tournaments'
    ordering = ['-created_at']


class MatchDetailView(LoginRequiredMixin, DetailView):
    model = Tournament
    template_name = 'matches/match_detail.html'
    context_object_name = 'tournament'
