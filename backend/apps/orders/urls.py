"""URL configuration for orders app."""
from django.urls import path

from .views import OrderDetailView, OrderListCreateView, ActiveBankCardView, PaymentProofUploadView

urlpatterns = [
    path('bank-card/', ActiveBankCardView.as_view(), name='active-bank-card'),
    path('orders/', OrderListCreateView.as_view(), name='order-list'),
    path('orders/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('orders/<int:pk>/proof/', PaymentProofUploadView.as_view(), name='order-proof-upload'),
]
