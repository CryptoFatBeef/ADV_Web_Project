from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, ListView, UpdateView

from apps.accounts.mixins import RoleRequiredMixin
from apps.members.models import MemberProfile

COACH_ROLES = ['GRANDMASTER', 'DEPUTY_GRANDMASTER', 'ADMIN', 'COACH']
ADMIN_ROLES = ['GRANDMASTER', 'DEPUTY_GRANDMASTER', 'ADMIN']


class MemberListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    roles = COACH_ROLES
    model = MemberProfile
    template_name = 'members/member_list.html'
    context_object_name = 'members'


class MemberDetailView(LoginRequiredMixin, RoleRequiredMixin, DetailView):
    roles = COACH_ROLES
    model = MemberProfile
    template_name = 'members/member_detail.html'
    context_object_name = 'member'


class MemberUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    roles = ADMIN_ROLES
    model = MemberProfile
    template_name = 'members/member_form.html'
    fields = ['status', 'current_belt', 'tier', 'primary_dojo', 'public_showcase_consent']

    def get_success_url(self):
        return self.object.get_absolute_url() if hasattr(self.object, 'get_absolute_url') \
            else f'/members/{self.object.pk}/'
