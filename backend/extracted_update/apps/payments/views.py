"""
Payments views.

Mock mode (PAYMENTS_MOCK_MODE=True):
  POST /api/payments/payme/checkout/  →  {"mock": true, "order_id": X}  (marks order paid)
  POST /api/payments/click/checkout/  →  {"mock": true, "order_id": X}  (marks order paid)

Real mode (PAYMENTS_MOCK_MODE=False):
  Same endpoints return {"checkout_url": "https://..."} and redirect client.

Callbacks (always active, used by payment providers):
  POST /api/payments/payme/callback/  →  Payme JSON-RPC webhook
  POST /api/payments/click/callback/  →  Click Prepare/Complete webhook
"""
import base64
import binascii
import logging

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order
from apps.payments.click import build_checkout_url as click_checkout_url
from apps.payments.click import click_handler
from apps.payments.payme import build_checkout_url as payme_checkout_url
from apps.payments.payme import payme_handler

logger = logging.getLogger(__name__)


# ─── Helper: verify Payme Basic Auth ─────────────────────────────────────────

def _verify_payme_basic_auth(request) -> bool:
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Basic '):
        return False
    try:
        decoded = base64.b64decode(auth[6:]).decode()
        _, password = decoded.split(':', 1)
        return password == settings.PAYME_SECRET_KEY
    except (binascii.Error, ValueError):
        return False


# ─── Checkout views ───────────────────────────────────────────────────────────

class PaymeCheckoutView(APIView):
    """POST /api/payments/payme/checkout/   body: {"order_id": <int>}"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_id = request.data.get('order_id')
        try:
            order = Order.objects.get(pk=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({'detail': 'Buyurtma topilmadi.'}, status=status.HTTP_404_NOT_FOUND)

        if order.payment_status == Order.PaymentStatus.PAID:
            return Response({'detail': "Buyurtma allaqachon to'langan."}, status=status.HTTP_400_BAD_REQUEST)

        if settings.PAYMENTS_MOCK_MODE:
            order.payment_status = Order.PaymentStatus.PAID
            order.save(update_fields=['payment_status'])
            logger.info('[MOCK] Payme: order #%s marked as paid', order.pk)
            return Response({'mock': True, 'order_id': order.pk, 'payment_status': 'paid'})

        return Response({'checkout_url': payme_checkout_url(order)})


class ClickCheckoutView(APIView):
    """POST /api/payments/click/checkout/   body: {"order_id": <int>}"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_id = request.data.get('order_id')
        try:
            order = Order.objects.get(pk=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({'detail': 'Buyurtma topilmadi.'}, status=status.HTTP_404_NOT_FOUND)

        if order.payment_status == Order.PaymentStatus.PAID:
            return Response({'detail': "Buyurtma allaqachon to'langan."}, status=status.HTTP_400_BAD_REQUEST)

        if settings.PAYMENTS_MOCK_MODE:
            order.payment_status = Order.PaymentStatus.PAID
            order.save(update_fields=['payment_status'])
            logger.info('[MOCK] Click: order #%s marked as paid', order.pk)
            return Response({'mock': True, 'order_id': order.pk, 'payment_status': 'paid'})

        return_url = settings.FRONTEND_URL
        return Response({'checkout_url': click_checkout_url(order, return_url=return_url)})


# ─── Webhook / Callback views ──────────────────────────────────────────────────

class PaymeCallbackView(APIView):
    """
    POST /api/payments/payme/callback/
    Receives Payme JSON-RPC 2.0 calls. Authenticates via Basic Auth using PAYME_SECRET_KEY.
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # No DRF auth — uses own Basic Auth check

    def post(self, request):
        if not _verify_payme_basic_auth(request):
            return Response(
                {
                    'jsonrpc': '2.0',
                    'id': request.data.get('id'),
                    'error': {'code': -32504, 'message': 'Unauthorized'},
                },
                status=status.HTTP_200_OK,  # Payme always expects 200
            )

        result = payme_handler.handle(request.data)
        return Response(result, status=status.HTTP_200_OK)


class ClickCallbackView(APIView):
    """
    POST /api/payments/click/callback/
    Receives Click Prepare (action=0) and Complete (action=1) callbacks.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        action = int(request.data.get('action', -1))
        if action == 0:
            result = click_handler.prepare(request.data)
        elif action == 1:
            result = click_handler.complete(request.data)
        else:
            result = {'error': -1, 'error_note': 'Unknown action'}

        return Response(result, status=status.HTTP_200_OK)
