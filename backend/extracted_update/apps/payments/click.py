"""
Click Merchant API handler.

Implements the Prepare (action=0) and Complete (action=1) flow.

Reference: https://docs.click.uz/click-api-1/

Sign string for Prepare:
    MD5(click_trans_id + service_id + SECRET_KEY + merchant_trans_id + amount + action + sign_time)

Sign string for Complete:
    MD5(click_trans_id + service_id + SECRET_KEY + merchant_trans_id + merchant_prepare_id + amount + action + sign_time)
"""
import hashlib
import logging
from decimal import Decimal

from django.conf import settings
from django.utils import timezone as tz

from apps.orders.models import Order
from apps.payments.models import ClickTransaction

logger = logging.getLogger(__name__)

# ─── Click error codes ────────────────────────────────────────────────────────
CLICK_OK = 0
CLICK_SIGN_FAILED = -1
CLICK_ORDER_NOT_FOUND = -5
CLICK_ALREADY_PAID = -4
CLICK_TRANSACTION_NOT_FOUND = -6
CLICK_CANCELLED = -9


def _md5(*parts: str) -> str:
    data = ''.join(str(p) for p in parts)
    return hashlib.md5(data.encode()).hexdigest()


class ClickHandler:
    """Handles Click Prepare and Complete webhook requests."""

    def prepare(self, data: dict) -> dict:
        """
        action=0: Validate sign and create ClickTransaction record.
        """
        click_trans_id = data.get('click_trans_id')
        service_id = data.get('service_id')
        merchant_trans_id = data.get('merchant_trans_id')  # order_id
        amount = data.get('amount')
        action = data.get('action', 0)
        sign_time = data.get('sign_time', '')
        received_sign = data.get('sign_string', '')

        # ── Signature check ────────────────────────────────────────────────
        expected_sign = _md5(
            click_trans_id, service_id, settings.CLICK_SECRET_KEY,
            merchant_trans_id, amount, action, sign_time,
        )
        if received_sign != expected_sign:
            return self._response(click_trans_id, merchant_trans_id,
                                  CLICK_SIGN_FAILED, "Noto'g'ri imzo")

        # ── Order check ────────────────────────────────────────────────────
        try:
            order = Order.objects.get(pk=int(merchant_trans_id))
        except (Order.DoesNotExist, ValueError):
            return self._response(click_trans_id, merchant_trans_id,
                                  CLICK_ORDER_NOT_FOUND, 'Buyurtma topilmadi')

        if order.payment_status == Order.PaymentStatus.PAID:
            return self._response(click_trans_id, merchant_trans_id,
                                  CLICK_ALREADY_PAID, "Allaqachon to'langan")

        # ── Create or retrieve ClickTransaction ────────────────────────────
        txn, _ = ClickTransaction.objects.get_or_create(
            click_trans_id=click_trans_id,
            defaults={
                'order': order,
                'merchant_trans_id': str(merchant_trans_id),
                'amount': Decimal(str(amount)),
                'sign_time': sign_time,
                'status': ClickTransaction.Status.WAITING,
            },
        )

        return self._response(
            click_trans_id, merchant_trans_id, CLICK_OK, '',
            merchant_prepare_id=txn.pk,
        )

    def complete(self, data: dict) -> dict:
        """
        action=1: Verify and finalise payment.
        """
        click_trans_id = data.get('click_trans_id')
        service_id = data.get('service_id')
        merchant_trans_id = data.get('merchant_trans_id')
        merchant_prepare_id = data.get('merchant_prepare_id')
        amount = data.get('amount')
        action = data.get('action', 1)
        sign_time = data.get('sign_time', '')
        received_sign = data.get('sign_string', '')
        error = int(data.get('error', 0))

        # ── Signature check ────────────────────────────────────────────────
        expected_sign = _md5(
            click_trans_id, service_id, settings.CLICK_SECRET_KEY,
            merchant_trans_id, merchant_prepare_id, amount, action, sign_time,
        )
        if received_sign != expected_sign:
            return self._response(click_trans_id, merchant_trans_id,
                                  CLICK_SIGN_FAILED, "Noto'g'ri imzo")

        # ── Fetch transaction ──────────────────────────────────────────────
        try:
            txn = ClickTransaction.objects.select_related('order').get(
                pk=int(merchant_prepare_id),
                click_trans_id=click_trans_id,
            )
        except (ClickTransaction.DoesNotExist, ValueError):
            return self._response(click_trans_id, merchant_trans_id,
                                  CLICK_TRANSACTION_NOT_FOUND, 'Tranzaksiya topilmadi')

        if txn.status == ClickTransaction.Status.CONFIRMED:
            return self._response(click_trans_id, merchant_trans_id,
                                  CLICK_ALREADY_PAID, "Allaqachon to'langan",
                                  merchant_prepare_id=txn.pk)

        # ── Click-side error (payment failed on their side) ────────────────
        if error < 0:
            txn.status = ClickTransaction.Status.CANCELLED
            txn.error = error
            txn.save(update_fields=['status', 'error'])
            txn.order.payment_status = Order.PaymentStatus.FAILED
            txn.order.save(update_fields=['payment_status'])
            return self._response(click_trans_id, merchant_trans_id,
                                  CLICK_CANCELLED, "To'lov bekor qilindi",
                                  merchant_prepare_id=txn.pk)

        # ── Confirm payment ────────────────────────────────────────────────
        txn.click_paydoc_id = data.get('click_paydoc_id')
        txn.status = ClickTransaction.Status.CONFIRMED
        txn.save(update_fields=['click_paydoc_id', 'status'])

        order = txn.order
        order.payment_status = Order.PaymentStatus.PAID
        order.save(update_fields=['payment_status'])

        return self._response(click_trans_id, merchant_trans_id, CLICK_OK, '',
                              merchant_prepare_id=txn.pk)

    @staticmethod
    def _response(
        click_trans_id,
        merchant_trans_id,
        error: int,
        error_note: str,
        merchant_prepare_id=None,
        merchant_confirm_id=None,
    ) -> dict:
        resp = {
            'click_trans_id': click_trans_id,
            'merchant_trans_id': merchant_trans_id,
            'error': error,
            'error_note': error_note,
        }
        if merchant_prepare_id is not None:
            resp['merchant_prepare_id'] = merchant_prepare_id
        if merchant_confirm_id is not None:
            resp['merchant_confirm_id'] = merchant_confirm_id
        return resp


# ─── Checkout URL builder ─────────────────────────────────────────────────────

def build_checkout_url(order: Order, return_url: str = '') -> str:
    """
    Click checkout URL:
    https://my.click.uz/services/pay?service_id=X&merchant_id=Y&amount=Z
        &transaction_param=ORDER_ID&return_url=...
    """
    from django.conf import settings as s
    from urllib.parse import urlencode

    params = {
        'service_id': s.CLICK_SERVICE_ID,
        'merchant_id': s.CLICK_MERCHANT_ID,
        'amount': order.total,
        'transaction_param': order.pk,
    }
    if return_url:
        params['return_url'] = return_url

    return 'https://my.click.uz/services/pay?' + urlencode(params)


click_handler = ClickHandler()
