from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.public.urls')),
    path('enroll/', include('apps.enrollment.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('members/', include('apps.members.urls')),
    path('dojos/', include('apps.dojos.urls')),
    path('events/', include('apps.events.urls')),
    path('activities/', include('apps.activities.urls')),
    path('skills/', include('apps.skills.urls')),
    path('fees/', include('apps.fees.urls')),
    path('payments/', include('apps.payments.urls')),
    path('communications/', include('apps.communications.urls')),
    path('cms/', include('apps.cms.urls')),
    path('matches/', include('apps.matches.urls')),
    path('chatbot/', include('apps.chatbot.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    import debug_toolbar
    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
