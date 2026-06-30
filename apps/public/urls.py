from django.urls import path

from apps.public.views import (
    AboutView,
    HomeView,
    InstructorListView,
    NewsDetailView,
    NewsListView,
    PublicDojoDetailView,
    PublicDojoListView,
    RobotsTxtView,
    ShowcaseListView,
)

app_name = 'public'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('about/', AboutView.as_view(), name='about'),
    path('instructors/', InstructorListView.as_view(), name='instructors'),
    path('our-dojos/', PublicDojoListView.as_view(), name='dojo_list'),
    path('our-dojos/<slug:slug>/', PublicDojoDetailView.as_view(), name='dojo_detail'),
    path('news/', NewsListView.as_view(), name='news_list'),
    path('news/<slug:slug>/', NewsDetailView.as_view(), name='news_detail'),
    path('showcase/', ShowcaseListView.as_view(), name='showcase_list'),
    path('robots.txt', RobotsTxtView.as_view(), name='robots_txt'),
]
