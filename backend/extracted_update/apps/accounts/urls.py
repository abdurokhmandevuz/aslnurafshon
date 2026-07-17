"""URL configuration for accounts app."""
from django.urls import path

from .views import AddressDetailView, AddressListCreateView, ProfileView

urlpatterns = [
    path('profile/', ProfileView.as_view(), name='profile'),
    path('addresses/', AddressListCreateView.as_view(), name='address-list'),
    path('addresses/<int:pk>/', AddressDetailView.as_view(), name='address-detail'),
]
