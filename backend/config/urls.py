"""Root URL configuration for Nurafshon backend."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from apps.orders.views_ssr import set_language_exempt

urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('set-language-exempt/', set_language_exempt, name='set_language_exempt'),
    
    # API endpoints (kept for webhooks & ajax)
    path('api/accounts/', include('apps.accounts.urls')),
    path('api/catalog/', include('apps.catalog.urls')),
    path('api/', include('apps.orders.urls')),
    path('api/', include('apps.payments.urls')),
    
    # SSR Views
    path('', include('apps.accounts.urls_ssr')),
    path('', include('apps.catalog.urls_ssr')),
    path('', include('apps.orders.urls_ssr')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
