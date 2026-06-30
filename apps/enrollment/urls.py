from django.urls import path

from apps.enrollment.views import EnrollmentCreateView, EnrollmentThanksView

app_name = 'enrollment'

urlpatterns = [
    path('', EnrollmentCreateView.as_view(), name='lead_create'),
    path('thanks/', EnrollmentThanksView.as_view(), name='lead_thanks'),
]
