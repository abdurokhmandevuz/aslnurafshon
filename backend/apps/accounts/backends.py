from django.contrib.auth.backends import BaseBackend
from apps.accounts.models import TelegramUser

class TelegramBackend(BaseBackend):
    """
    Custom authentication backend that authenticates TelegramUser.
    Required because TelegramUser is not a subclass of standard django User,
    and standard ModelBackend queries the standard auth_user table.
    """
    def authenticate(self, request, **kwargs):
        # Authentication is handled by TelegramInitDataAuthentication or custom views
        return None

    def get_user(self, user_id):
        try:
            return TelegramUser.objects.get(pk=user_id)
        except TelegramUser.DoesNotExist:
            return None
