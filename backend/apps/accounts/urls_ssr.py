from django.urls import path
from .views_ssr import auth_telegram_view, splash_screen_view, profile_view
from .views_courier import courier_dashboard_view, courier_order_action_view

urlpatterns = [
    path('', splash_screen_view, name='splash'),
    path('start/', splash_screen_view, name='splash_start'),
    path('auth/telegram/', auth_telegram_view, name='auth_telegram'),
    path('profile/', profile_view, name='profile'),
    
    # Courier Panel
    path('courier/', courier_dashboard_view, name='courier_dashboard'),
    path('courier/order/<int:order_id>/<str:action>/', courier_order_action_view, name='courier_order_action'),
]
