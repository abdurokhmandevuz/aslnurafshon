"""Views for orders app."""
import logging

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser

from .models import Order, BankCard
from .serializers import (
    OrderCreateSerializer, OrderDetailSerializer, OrderListSerializer, BankCardSerializer
)

logger = logging.getLogger(__name__)


class ActiveBankCardView(APIView):
    """GET /api/bank-card/ — returns active bank card details for manual payment."""
    permission_classes = []

    def get(self, request):
        card = BankCard.objects.filter(is_active=True).first()
        if not card:
            card = BankCard.objects.create(
                bank_name="Kapitalbank",
                card_number="8600 1234 5678 9012",
                card_holder="ASL NURAFSHON",
                is_active=True
            )
        serializer = BankCardSerializer(card)
        return Response(serializer.data)


class PaymentProofUploadView(APIView):
    """POST /api/orders/<id>/proof/ — upload receipt image for an order."""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        try:
            order = Order.objects.get(pk=pk, user=request.user)
        except Order.DoesNotExist:
            return Response({'error': 'Buyurtma topilmadi'}, status=status.HTTP_404_NOT_FOUND)

        file_obj = request.FILES.get('payment_proof') or request.FILES.get('file') or request.FILES.get('image')
        if not file_obj:
            return Response({'error': 'Fayl yuborilmadi'}, status=status.HTTP_400_BAD_REQUEST)

        order.payment_proof = file_obj
        order.save(update_fields=['payment_proof'])

        from bot.notifications import notify_new_order
        import asyncio
        try:
            asyncio.create_task(notify_new_order(order.pk))
        except Exception as exc:
            logger.warning("Failed to trigger notify_new_order task: %s", exc)

        return Response({
            'message': 'Chek muvaffaqiyatli yuklandi',
            'order_id': order.id,
            'payment_proof': order.payment_proof.url if order.payment_proof else None
        })


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
