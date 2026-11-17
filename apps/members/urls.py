from django.urls import path

from apps.members.views import (
    MemberDetailView,
    MemberInvitationCreateView,
    MemberListView,
    MemberOnboardingThanksView,
    MemberOnboardingView,
    MemberUpdateView,
)

app_name = 'members'

urlpatterns = [
    path('', MemberListView.as_view(), name='member_list'),
    path('invite/', MemberInvitationCreateView.as_view(), name='invitation_create'),
    path('onboarding/<uuid:token>/', MemberOnboardingView.as_view(), name='onboarding'),
    path('onboarding/<uuid:token>/thanks/', MemberOnboardingThanksView.as_view(), name='onboarding_thanks'),
    path('<int:pk>/', MemberDetailView.as_view(), name='member_detail'),
    path('<int:pk>/edit/', MemberUpdateView.as_view(), name='member_edit'),
]
