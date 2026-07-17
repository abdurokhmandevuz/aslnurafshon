"""URL configuration for payments app."""
from django.urls import path

from .views import (
    ClickCallbackView,
    ClickCheckoutView,
    PaymeCallbackView,
    PaymeCheckoutView,
)

urlpatterns = [
    # Checkout link generators (auth required)
    path('payments/payme/checkout/', PaymeCheckoutView.as_view(), name='payme-checkout'),
    path('payments/click/checkout/', ClickCheckoutView.as_view(), name='click-checkout'),

    # Webhook callbacks (called by payment providers, no user auth)
    path('payments/payme/callback/', PaymeCallbackView.as_view(), name='payme-callback'),
    path('payments/click/callback/', ClickCallbackView.as_view(), name='click-callback'),
]
