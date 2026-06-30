from django.urls import path

from apps.skills.views import SkillListView

app_name = 'skills'

urlpatterns = [
    path('', SkillListView.as_view(), name='skill_list'),
]
