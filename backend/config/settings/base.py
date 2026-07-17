"""
Base Django settings for Nurafshon project.
All environment-specific settings live in local.py / production.py.
"""
from pathlib import Path

from decouple import config, Csv

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ─── Security ────────────────────────────────────────────────────────────────
SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-key-change-in-prod')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*', cast=Csv())

# ─── Applications ─────────────────────────────────────────────────────────────
DJANGO_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'corsheaders',
    'django_filters',
]

LOCAL_APPS = [
    'apps.accounts',
    'apps.catalog',
    'apps.orders',
    'apps.payments',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ─── Middleware ───────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'config.middleware.RateLimitMiddleware',
    'config.middleware.NoCacheMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'config.middleware.CourierRedirectMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.orders.context_processors.cart_processor',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# ─── Database ─────────────────────────────────────────────────────────────────
# Configured in local.py / production.py via DATABASE_URL

# ─── Auth ─────────────────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─── Internationalisation ─────────────────────────────────────────────────────
LANGUAGE_CODE = 'uz'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True

from django.utils.translation import gettext_lazy as _
LANGUAGES = [
    ('uz', _('Uzbek')),
    ('ru', _('Russian')),
]
LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# ─── Static / Media ──────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ─── Sessions ────────────────────────────────────────────────────────────────
SESSION_COOKIE_AGE = 2592000  # 30 days


MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTHENTICATION_BACKENDS = [
    'apps.accounts.backends.TelegramBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# ─── Django REST Framework ────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'apps.accounts.authentication.TelegramInitDataAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# ─── CORS ────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='https://nurafshon.vercel.app',
    cast=Csv(),
)
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='https://aslnurafshon.duckdns.org',
    cast=Csv(),
)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_COOKIE_SAMESITE = 'None'
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_SECURE = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'telegram-data',
]

# ─── Bot & Frontend ──────────────────────────────────────────────────────────
BOT_TOKEN = config('BOT_TOKEN', default='')
BOT_WEBHOOK_URL = config('BOT_WEBHOOK_URL', default='')
ADMIN_GROUP_ID = config('ADMIN_GROUP_ID', default='', cast=lambda x: int(x) if x else None)
CLICK_PROVIDER_TOKEN = config('CLICK_PROVIDER_TOKEN', default='')
FRONTEND_URL = config('FRONTEND_URL', default='https://nurafshon.vercel.app')

# ─── Payments ─────────────────────────────────────────────────────────────────
PAYMENTS_MOCK_MODE = config('PAYMENTS_MOCK_MODE', default=True, cast=bool)

PAYME_MERCHANT_ID = config('PAYME_MERCHANT_ID', default='')
PAYME_SECRET_KEY = config('PAYME_SECRET_KEY', default='')
PAYME_TEST_MODE = config('PAYME_TEST_MODE', default=True, cast=bool)
PAYME_CHECKOUT_BASE_URL = config(
    'PAYME_CHECKOUT_BASE_URL',
    default='https://checkout.test.paycom.uz',
)

CLICK_SERVICE_ID = config('CLICK_SERVICE_ID', default='')
CLICK_MERCHANT_ID = config('CLICK_MERCHANT_ID', default='')
CLICK_SECRET_KEY = config('CLICK_SECRET_KEY', default='')
CLICK_TEST_MODE = config('CLICK_TEST_MODE', default=True, cast=bool)

# ─── Delivery ────────────────────────────────────────────────────────────────
# Amount in UZS tiyin (1 so'm = 100 tiyin). Default: 15 000 so'm = 1 500 000 tiyin
DEFAULT_DELIVERY_FEE = config('DEFAULT_DELIVERY_FEE', default=1500000, cast=int)


# ─── Jazzmin Settings ────────────────────────────────────────────────────────
JAZZMIN_SETTINGS = {
    "site_title": "Asl Nurafshon Admin",
    "site_header": "Asl Nurafshon",
    "site_brand": "Asl Nurafshon",
    "site_logo_classes": "img-circle",
    "welcome_sign": "Asl Nurafshon Boshqaruv Paneliga xush kelibsiz",
    "copyright": "Asl Nurafshon Ltd",
    "search_model": "catalog.Product",
    "user_avatar": None,
    "topmenu_links": [
        {"name": "Bosh sahifa",  "url": "admin:index", "permissions": ["auth.view_user"]},
        {"model": "catalog.Product"},
        {"model": "orders.Order"},
    ],
    "usermenu_links": [
        {"name": "Katalog ko'rish", "url": "/catalog/", "new_tab": True},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],
    "order_with_respect_to": ["catalog", "orders", "payments", "accounts"],
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "accounts.TelegramUser": "fas fa-paper-plane",
        "accounts.Address": "fas fa-map-marker-alt",
        "accounts.Courier": "fas fa-shipping-fast",
        "catalog.Category": "fas fa-list",
        "catalog.Product": "fas fa-box",
        "catalog.ProductVariant": "fas fa-boxes",
        "catalog.Banner": "fas fa-image",
        "catalog.FavoriteProduct": "fas fa-heart",
        "catalog.DailyDeal": "fas fa-bolt",
        "catalog.ProductReview": "fas fa-star",
        "catalog.ProductBundle": "fas fa-gift",
        "catalog.BundleItem": "fas fa-dolly",
        "orders.Order": "fas fa-shopping-cart",
        "orders.OrderItem": "fas fa-shopping-basket",
        "orders.TimeSlot": "fas fa-clock",
        "orders.FeedbackRequest": "fas fa-poll",
        "orders.CorporateInquiry": "fas fa-building",
        "payments.Payment": "fas fa-money-bill-wave",
    },
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    "related_modal_active": False,
    "show_ui_builder": False,
    "change_list_template_extends": "admin/change_list.html",
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-dark",
    "accent": "accent-primary",
    "navbar": "navbar-dark bg-dark",
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_fixed": True,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "flatly",
    "dark_mode_theme": "darkly",
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    }
}
