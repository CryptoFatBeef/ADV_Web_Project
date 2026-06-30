from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView

from apps.enrollment.forms import EnrollmentLeadForm
from apps.enrollment.models import EnrollmentLead


class EnrollmentCreateView(CreateView):
    model = EnrollmentLead
    form_class = EnrollmentLeadForm
    template_name = 'enrollment/lead_form.html'
    success_url = reverse_lazy('enrollment:lead_thanks')


class EnrollmentThanksView(TemplateView):
    template_name = 'enrollment/lead_thanks.html'
