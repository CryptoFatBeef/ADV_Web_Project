from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, DetailView, ListView

from apps.accounts.mixins import RoleRequiredMixin
from apps.events.models import Event

ADMIN_ROLES = ['GRANDMASTER', 'DEPUTY_GRANDMASTER', 'ADMIN']


class EventListView(LoginRequiredMixin, ListView):
    model = Event
    template_name = 'events/event_list.html'
    context_object_name = 'events'
    ordering = ['-start_datetime']


class EventDetailView(LoginRequiredMixin, DetailView):
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
