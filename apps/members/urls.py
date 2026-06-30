from django.urls import path

from apps.members.views import MemberDetailView, MemberListView, MemberUpdateView

app_name = 'members'

urlpatterns = [
    path('', MemberListView.as_view(), name='member_list'),
    path('<int:pk>/', MemberDetailView.as_view(), name='member_detail'),
    path('<int:pk>/edit/', MemberUpdateView.as_view(), name='member_edit'),
]
