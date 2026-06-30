from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from apps.skills.models import SkillRecord


class SkillListView(LoginRequiredMixin, ListView):
    model = SkillRecord
    template_name = 'skills/skill_list.html'
    context_object_name = 'skills'
    ordering = ['-assessed_at']
