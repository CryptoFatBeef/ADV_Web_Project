from django.conf import settings


def site_settings(request):
    return {
        'SITE_DOMAIN': settings.SITE_DOMAIN,
        'SITE_FACEBOOK_URL': settings.SITE_FACEBOOK_URL,
        'SITE_INSTAGRAM_URL': settings.SITE_INSTAGRAM_URL,
    }
