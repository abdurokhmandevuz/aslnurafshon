from django.urls import path
from . import views_ssr

urlpatterns = [
    path('cart/', views_ssr.cart_view, name='cart'),
    path('cart/update/', views_ssr.cart_update_view, name='cart_update'),
    path('checkout/', views_ssr.checkout_view, name='checkout'),
    path('checkout/submit/', views_ssr.checkout_submit_view, name='checkout_submit'),
    path('checkout/success/', views_ssr.order_success_view, name='order_success'),
    path('orders/', views_ssr.orders_view, name='orders'),
]
