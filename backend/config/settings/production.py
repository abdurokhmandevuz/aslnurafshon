"""Production settings for Oracle Cloud / DuckDNS deployment."""
import dj_database_url
from decouple import config

from .base import *  # noqa: F401,F403

DEBUG = False

# ─── Database (Local PostgreSQL on Oracle) ────────────────────────────────────
DATABASES = {
    'default': dj_database_url.parse(
        clean_env_value(config('DATABASE_URL')),
        conn_max_age=600,
        ssl_require=False,  # Local PostgreSQL on Oracle — SSL not needed
    )
}

# ─── Security ─────────────────────────────────────────────────────────────────
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = False  # Nginx handles SSL redirect
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# ─── Session / Cookie settings for Telegram Mini App ─────────────────────────
# Telegram WebApp embeds pages — cookies MUST be SameSite=None + Secure
SESSION_COOKIE_SAMESITE = 'None'
CSRF_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30  # 30 kun
SESSION_COOKIE_HTTPONLY = True
SESSION_SAVE_EVERY_REQUEST = True  # har so'rovda sessiyani yangilash

# ─── Logging ──────────────────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            'format': '%(levelname)s %(asctime)s %(name)s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        'apps': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'bot': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}
