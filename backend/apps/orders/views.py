"""Views for orders app."""
import logging

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Order
from .serializers import OrderCreateSerializer, OrderDetailSerializer, OrderListSerializer

logger = logging.getLogger(__name__)


class OrderListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/orders/ — list authenticated user's orders (newest first)
    POST /api/orders/ — create a new order
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Order.objects.filter(user=self.request.user)
            .prefetch_related('items')
            .select_related('address')
            .order_by('-created_at')
        )

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return OrderCreateSerializer
        return OrderListSerializer

    def create(self, request, *args, **kwargs):
        serializer = OrderCreateSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        # Emit signal → background thread → Telegram notifications
        from apps.orders.signals import order_created as order_created_signal
        order_created_signal.send(sender=Order, order=order)

        detail = OrderDetailSerializer(order, context={'request': request})
        return Response(detail.data, status=status.HTTP_201_CREATED)


class OrderDetailView(generics.RetrieveAPIView):
    """GET /api/orders/<id>/"""

    serializer_class = OrderDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Order.objects.filter(user=self.request.user)
            .prefetch_related('items')
            .select_related('address')
        )
