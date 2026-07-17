"""
Custom DRF authentication backend for Telegram WebApp initData.

Usage
-----
Frontend sends:
    Authorization: TelegramInitData <url-encoded initData string>

Backend verifies HMAC-SHA256 signature using BOT_TOKEN, then
auto-creates or updates the TelegramUser and binds it to request.user.

Debug bypass
------------
When DEBUG=True, passing "Authorization: TelegramInitData debug" skips HMAC
verification and returns a fixed test user (telegram_id=0).
"""
import hashlib
import hmac
import json
import logging
import urllib.parse

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from apps.accounts.models import TelegramUser

logger = logging.getLogger(__name__)


class TelegramInitDataAuthentication(BaseAuthentication):
    """Authenticate requests via Telegram WebApp initData."""

    HEADER_PREFIX = 'TelegramInitData '

    # ------------------------------------------------------------------
    # DRF interface
    # ------------------------------------------------------------------

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith(self.HEADER_PREFIX):
            return None  # Let other authenticators try

        raw_init_data = auth_header[len(self.HEADER_PREFIX):]

        # ── Debug shortcut ────────────────────────────────────────────
        if settings.DEBUG and raw_init_data.strip() == 'debug':
            user, _ = TelegramUser.objects.get_or_create(
                telegram_id=0,
                defaults={
                    'full_name': 'Debug User',
                    'username': 'debug',
                    'language_code': 'uz',
                },
            )
            logger.debug('TelegramAuth: debug bypass, user=%s', user)
            return (user, None)

        # ── Real validation ───────────────────────────────────────────
        try:
            user_data = self._validate_and_parse(raw_init_data)
        except AuthenticationFailed:
            raise
        except Exception as exc:
            logger.exception('TelegramAuth: unexpected error: %s', exc)
            raise AuthenticationFailed('initData validation failed')

        user = self._get_or_create_user(user_data)
        return (user, None)

    def authenticate_header(self, request):
        return 'TelegramInitData'

    # ------------------------------------------------------------------
    # Validation logic
    # ------------------------------------------------------------------

    def _validate_and_parse(self, init_data: str) -> dict:
        """
        Validate Telegram WebApp initData per official spec:
        https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
        Returns parsed 'user' dict on success.
        Raises AuthenticationFailed on failure.
        """
        # Parse query string — keep original percent-encoding decoded values
        try:
            parsed = urllib.parse.parse_qs(init_data, keep_blank_values=True)
        except Exception:
            raise AuthenticationFailed('Malformed initData')

        received_hash = parsed.pop('hash', [None])[0]
        if not received_hash:
            raise AuthenticationFailed('Missing hash field in initData')

        # Build data-check string: sorted key=value pairs joined by \n
        pairs = []
        for key in sorted(parsed.keys()):
            pairs.append(f'{key}={parsed[key][0]}')
        data_check_string = '\n'.join(pairs)

        # Secret key: HMAC-SHA256( key="WebAppData", msg=bot_token )
        bot_token_bytes = settings.BOT_TOKEN.encode()
        secret_key = hmac.new(
            key=b'WebAppData',
            msg=bot_token_bytes,
            digestmod=hashlib.sha256,
        ).digest()

        # Computed hash: HMAC-SHA256( key=secret_key, msg=data_check_string )
        computed_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode(),
            digestmod=hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(computed_hash, received_hash):
            raise AuthenticationFailed('initData signature mismatch')

        # Parse user object
        user_raw = parsed.get('user', ['{}'])[0]
        try:
            user_data = json.loads(user_raw)
        except json.JSONDecodeError:
            raise AuthenticationFailed('Invalid user JSON in initData')

        if 'id' not in user_data:
            raise AuthenticationFailed('Missing user.id in initData')

        return user_data

    def _get_or_create_user(self, user_data: dict) -> TelegramUser:
        """Create or update TelegramUser from validated initData user dict."""
        first = user_data.get('first_name', '')
        last = user_data.get('last_name', '')
        full_name = f'{first} {last}'.strip() or f'User {user_data["id"]}'

        user, created = TelegramUser.objects.get_or_create(
            telegram_id=user_data['id'],
            defaults={
                'full_name': full_name,
                'username': user_data.get('username', ''),
                'language_code': user_data.get('language_code', 'uz'),
            },
        )

        if not created:
            changed = False
            if user.full_name != full_name:
                user.full_name = full_name
                changed = True
            if user.username != user_data.get('username', ''):
                user.username = user_data.get('username', '')
                changed = True
            if changed:
                user.save(update_fields=['full_name', 'username'])

        return user
