from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import TemplateView

from apps.dojos.models import DojoStaff
from apps.events.models import AttendanceLog, Event
from apps.fees.models import AnnualFee
from apps.members.models import MemberProfile


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        role = user.role

        if role in ['GRANDMASTER', 'DEPUTY_GRANDMASTER', 'ADMIN']:
            context['total_members'] = MemberProfile.objects.filter(status='ACTIVE').count()
            context['upcoming_events'] = Event.objects.filter(
                start_datetime__gte=timezone.now()
            ).order_by('start_datetime')[:5]
            context['pending_fees'] = AnnualFee.objects.filter(status='UNPAID').count()
            context['my_upcoming_events'] = []   # always supply so template |default filter works

        elif role == 'COACH':
            coach_dojos = DojoStaff.objects.filter(
                user=user, is_active=True
            ).values_list('dojo_id', flat=True)
            context['total_members'] = MemberProfile.objects.filter(
                enrollments__dojo_id__in=coach_dojos,
                status='ACTIVE',
            ).distinct().count()
            context['upcoming_events'] = Event.objects.filter(
                dojo_id__in=coach_dojos,
                start_datetime__gte=timezone.now(),
            ).order_by('start_datetime')[:5]
            context['pending_fees'] = None
            context['my_upcoming_events'] = []   # always supply so template |default filter works

        else:
            context['my_attendance'] = AttendanceLog.objects.filter(
                member__user=user
            ).count()
            context['my_upcoming_events'] = Event.objects.filter(
                start_datetime__gte=timezone.now()
            ).order_by('start_datetime')[:3]
            context['my_pending_fees'] = AnnualFee.objects.filter(
                member__user=user, status='UNPAID'
            ).count()
            context['upcoming_events'] = []   # always supply so template |default filter works

        return context


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/profile.html'
