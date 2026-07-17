"""Views for accounts app: profile and address management."""
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Address
from .serializers import AddressSerializer, TelegramUserSerializer


class ProfileView(generics.RetrieveUpdateAPIView):
    """GET /api/profile/ — return authenticated user's profile."""

    serializer_class = TelegramUserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class AddressListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/addresses/ — list user's saved addresses
    POST /api/addresses/ — create a new address
    """

    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/addresses/<id>/
    PATCH  /api/addresses/<id>/
    DELETE /api/addresses/<id>/
    """

    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)
