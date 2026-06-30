from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, ListView

from apps.dojos.models import DojoEntity


class DojoListView(LoginRequiredMixin, ListView):
    model = DojoEntity
    template_name = 'dojos/dojo_list.html'
    context_object_name = 'dojos'


class DojoDetailView(LoginRequiredMixin, DetailView):
    model = DojoEntity
    template_name = 'dojos/dojo_detail.html'
    context_object_name = 'dojo'
