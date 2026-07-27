"""Root URL configuration for Nurafshon backend."""
from django.contrib import admin
from django.http import JsonResponse, FileResponse, Http404
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

from apps.orders.views_ssr import set_language_exempt


import os
from django.views.static import serve as static_serve

# Support both local dev (../frontend) and Railway layout (../frontend)
_BASE = settings.BASE_DIR.parent
FRONTEND_DIR = str(_BASE / 'frontend')


def serve_frontend(request, path='index.html'):
    """Serve frontend HTML/JS/CSS files. Falls back to index.html for SPA routes."""
    if not path or path == '/':
        path = 'index.html'
    full_path = os.path.join(FRONTEND_DIR, path)
    if not os.path.exists(full_path):
        # Fall back to index.html for SPA-style routing
        path = 'index.html'
    return static_serve(request, path, document_root=FRONTEND_DIR)


def health_check(_request):
    return JsonResponse({'status': 'ok'})


urlpatterns = [
    path('health/', health_check, name='health_check'),
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

    # Frontend Static & HTML Routes — all asset types + SPA fallback
    path('', serve_frontend, kwargs={'path': 'index.html'}),
    re_path(r'^(?P<path>.*\.(html|js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot|json|webp|mp4|webm))$', serve_frontend),
    # Catch-all: unknown paths → index.html (SPA fallback)
    re_path(r'^(?!admin/|api/|health/|media/|static/|i18n/|set-language-exempt/)(?P<path>.+)$', serve_frontend),
]

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]
