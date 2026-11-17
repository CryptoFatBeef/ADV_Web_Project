from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, ListView

from apps.activities.models import ActivityEvent
from apps.dojos.models import DojoStaff


class DojoScopedQuerysetMixin:
    """
    Restricts the queryset to ActivityEvent sessions at the requesting
    COACH's own dojo(s), using ActivityEvent's direct `dojo` FK.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.role == 'COACH':
            coach_dojos = DojoStaff.objects.filter(
                user=self.request.user, is_active=True
            ).values_list('dojo_id', flat=True)
            qs = qs.filter(dojo_id__in=coach_dojos).distinct()
        return qs


class ActivityListView(LoginRequiredMixin, DojoScopedQuerysetMixin, ListView):
    model = ActivityEvent
    template_name = 'activities/activity_list.html'
    context_object_name = 'activities'
    ordering = ['-scheduled_date']


class ActivityDetailView(LoginRequiredMixin, DojoScopedQuerysetMixin, DetailView):
    model = ActivityEvent
    template_name = 'activities/activity_detail.html'
    context_object_name = 'activity'
