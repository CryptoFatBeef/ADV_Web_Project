from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from apps.accounts.forms import BootstrapAuthenticationForm
from apps.accounts.views import DashboardView, ProfileView

app_name = 'accounts'

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('login/', LoginView.as_view(
        template_name='accounts/login.html',
        authentication_form=BootstrapAuthenticationForm,
    ), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
]
