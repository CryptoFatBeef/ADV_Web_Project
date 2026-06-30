from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, ListView

from apps.activities.models import ActivityEvent


class ActivityListView(LoginRequiredMixin, ListView):
    model = ActivityEvent
    template_name = 'activities/activity_list.html'
    context_object_name = 'activities'
    ordering = ['-scheduled_date']


class ActivityDetailView(LoginRequiredMixin, DetailView):
    model = ActivityEvent
    template_name = 'activities/activity_detail.html'
    context_object_name = 'activity'
