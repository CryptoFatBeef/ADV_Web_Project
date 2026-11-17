from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, DetailView, ListView

from apps.accounts.mixins import RoleRequiredMixin
from apps.dojos.models import DojoStaff
from apps.events.models import Event

ADMIN_ROLES = ['GRANDMASTER', 'DEPUTY_GRANDMASTER', 'ADMIN']


class DojoScopedQuerysetMixin:
    """
    Restricts the queryset to events at the requesting COACH's own dojo(s).
    All other roles see all events unfiltered (matches the current design —
    only COACH access was unintentionally org-wide).
    """

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.role == 'COACH':
            coach_dojos = DojoStaff.objects.filter(
                user=self.request.user, is_active=True
            ).values_list('dojo_id', flat=True)
            qs = qs.filter(dojo_id__in=coach_dojos).distinct()
        return qs


class EventListView(LoginRequiredMixin, DojoScopedQuerysetMixin, ListView):
    model = Event
    template_name = 'events/event_list.html'
    context_object_name = 'events'
    ordering = ['-start_datetime']


class EventDetailView(LoginRequiredMixin, DojoScopedQuerysetMixin, DetailView):
    model = Event
    template_name = 'events/event_detail.html'
    context_object_name = 'event'


class EventCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    roles = ADMIN_ROLES
    model = Event
    template_name = 'events/event_form.html'
    fields = ['title', 'event_type', 'status', 'dojo', 'start_datetime', 'end_datetime', 'max_capacity', 'location']

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return f'/events/{self.object.pk}/'
