from django.urls import path

from apps.cms.views import CMSPageEditView, CMSPageListView

app_name = 'cms'

urlpatterns = [
    path('', CMSPageListView.as_view(), name='page_list'),
    path('<int:pk>/edit/', CMSPageEditView.as_view(), name='page_edit'),
]
