from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, UpdateView

from apps.accounts.mixins import RoleRequiredMixin
from apps.cms.models import ContentBlock

EDITOR_ROLES = ['GRANDMASTER', 'DEPUTY_GRANDMASTER', 'EDITOR']


class CMSPageListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    roles = EDITOR_ROLES
    model = ContentBlock
    template_name = 'cms/page_list.html'
    context_object_name = 'pages'
    ordering = ['section', 'order']


class CMSPageEditView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    roles = EDITOR_ROLES
    model = ContentBlock
    template_name = 'cms/page_form.html'
    fields = ['title', 'section', 'status', 'order', 'body', 'image', 'is_featured']

    def get_success_url(self):
        return '/cms/'
