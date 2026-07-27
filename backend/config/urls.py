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
import logging
logger = logging.getLogger(__name__)

possible_dirs = [
    os.path.join(settings.BASE_DIR.parent, 'frontend'),
    os.path.join(settings.BASE_DIR, 'frontend'),
    os.path.join(os.path.dirname(settings.BASE_DIR), 'frontend'),
    '/app/frontend',
    '/workspace/frontend',
]

FRONTEND_DIR = None
for d in possible_dirs:
    if os.path.exists(d) and os.path.isdir(d):
        FRONTEND_DIR = d
        break

if not FRONTEND_DIR:
    # Use default
    FRONTEND_DIR = os.path.join(settings.BASE_DIR.parent, 'frontend')
    logger.warning(f"FRONTEND_DIR NOT FOUND in standard locations! Falling back to: {FRONTEND_DIR}")
else:
    logger.info(f"Resolved FRONTEND_DIR at: {FRONTEND_DIR}")
    try:
        logger.info(f"Files in FRONTEND_DIR: {os.listdir(FRONTEND_DIR)}")
    except Exception as e:
        logger.warning(f"Could not list FRONTEND_DIR: {e}")


def serve_frontend(request, path='index.html'):
    """Serve frontend HTML/JS/CSS files. Falls back to index.html for SPA routes."""
    if not path or path == '/':
        path = 'index.html'
    full_path = os.path.join(FRONTEND_DIR, path)
    if not os.path.exists(full_path):
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
