from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from apps.dojos.models import DojoStaff
from apps.skills.models import SkillRecord


class SkillListView(LoginRequiredMixin, ListView):
    model = SkillRecord
    template_name = 'skills/skill_list.html'
    context_object_name = 'skills'
    ordering = ['-assessed_at']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == 'COACH':
            coach_dojos = DojoStaff.objects.filter(
                user=user, is_active=True
            ).values_list('dojo_id', flat=True)
            qs = qs.filter(member__enrollments__dojo_id__in=coach_dojos).distinct()
        elif user.role in ('MEMBER', 'PARENT'):
            qs = qs.filter(member__user=user).distinct()
        return qs
