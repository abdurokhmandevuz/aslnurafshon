from django.urls import path
from .views_ssr import auth_telegram_view, splash_screen_view, profile_view

urlpatterns = [
    path('', splash_screen_view, name='splash'),
    path('auth/telegram/', auth_telegram_view, name='auth_telegram'),
    path('profile/', profile_view, name='profile'),
]
