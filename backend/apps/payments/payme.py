"""
Payme Merchant API (JSON-RPC 2.0) handler.

Implements all required methods per Payme Business documentation:
  - CheckPerformTransaction
  - CreateTransaction
  - PerformTransaction
  - CancelTransaction
  - CheckTransaction
  - GetStatement

Reference: https://developer.paycom.uz/docs/
"""
import base64
import logging
from datetime import datetime, timezone

from django.conf import settings
from django.utils import timezone as tz

from apps.orders.models import Order
from apps.payments.models import PaymeTransaction

logger = logging.getLogger(__name__)

# ─── Error codes (Payme spec) ─────────────────────────────────────────────────
PAYME_ERROR = {
    'INVALID_AMOUNT':           {'code': -31001, 'message': {'uz': "Noto'g'ri summa", 'ru': 'Неверная сумма', 'en': 'Invalid amount'}},
    'TRANSACTION_NOT_FOUND':    {'code': -31003, 'message': {'uz': 'Tranzaksiya topilmadi', 'ru': 'Транзакция не найдена', 'en': 'Transaction not found'}},
    'ALREADY_DONE':             {'code': -31060, 'message': {'uz': 'Tranzaksiya allaqachon bajarildi', 'ru': 'Транзакция уже выполнена', 'en': 'Already done'}},
    'CANCELLED_TRANSACTION':    {'code': -31061, 'message': {'uz': 'Tranzaksiya bekor qilingan', 'ru': 'Транзакция отменена', 'en': 'Cancelled'}},
    'CANNOT_CANCEL_TRANSACTION':{'code': -31062, 'message': {'uz': "Tranzaksiyani bekor qilib bo'lmaydi", 'ru': 'Отмена невозможна', 'en': 'Cannot cancel'}},
    'ORDER_NOT_FOUND':          {'code': -31050, 'message': {'uz': 'Buyurtma topilmadi', 'ru': 'Заказ не найден', 'en': 'Order not found'}},
    'ORDER_ALREADY_PAID':       {'code': -31051, 'message': {'uz': "Buyurtma allaqachon to'langan", 'ru': 'Заказ уже оплачен', 'en': 'Already paid'}},
    'SERVER_ERROR':             {'code': -32400, 'message': {'uz': 'Server xatosi', 'ru': 'Ошибка сервера', 'en': 'Server error'}},
}


def _error_response(rpc_id, key: str):
    err = PAYME_ERROR[key]
    return {
        'jsonrpc': '2.0',
        'id': rpc_id,
        'error': {
            'code': err['code'],
            'message': err['message'],
            'data': key,
        },
    }


def _ok_response(rpc_id, result: dict):
    return {'jsonrpc': '2.0', 'id': rpc_id, 'result': result}


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


# ─── Handler ──────────────────────────────────────────────────────────────────

class PaymeHandler:
    """Dispatches Payme JSON-RPC calls to the appropriate method."""

    METHODS = {
        'CheckPerformTransaction',
        'CreateTransaction',
        'PerformTransaction',
        'CancelTransaction',
        'CheckTransaction',
        'GetStatement',
    }

    def handle(self, body: dict) -> dict:
        rpc_id = body.get('id')
        method = body.get('method')
        params = body.get('params', {})

        if method not in self.METHODS:
            return _error_response(rpc_id, 'SERVER_ERROR')

        handler_fn = getattr(self, f'_{method[0].lower()}{method[1:]}')
        try:
            return handler_fn(rpc_id, params)
        except Exception as exc:
            logger.exception('Payme %s error: %s', method, exc)
            return _error_response(rpc_id, 'SERVER_ERROR')

    # ── CheckPerformTransaction ────────────────────────────────────────────────

    def _checkPerformTransaction(self, rpc_id, params: dict) -> dict:
        """Verify that the order exists and amount matches."""
        order, err = self._get_order(rpc_id, params)
        if err:
            return err

        expected = order.total * 100  # convert so'm → tiyin
        if params['amount'] != expected:
            return _error_response(rpc_id, 'INVALID_AMOUNT')

        return _ok_response(rpc_id, {'allow': True})

    # ── CreateTransaction ──────────────────────────────────────────────────────

    def _createTransaction(self, rpc_id, params: dict) -> dict:
        order, err = self._get_order(rpc_id, params)
        if err:
            return err

        expected = order.total * 100
        if params['amount'] != expected:
            return _error_response(rpc_id, 'INVALID_AMOUNT')

        payme_id = params['id']
        payme_time = params['time']

        try:
            txn = PaymeTransaction.objects.get(payme_transaction_id=payme_id)
            if txn.state == PaymeTransaction.State.CREATED:
                return _ok_response(rpc_id, {
                    'create_time': int(txn.create_time.timestamp() * 1000),
                    'transaction': str(txn.pk),
                    'state': txn.state,
                })
            return _error_response(rpc_id, 'ALREADY_DONE')
        except PaymeTransaction.DoesNotExist:
            pass

        # Check for existing paid orders
        if order.payment_status == Order.PaymentStatus.PAID:
            return _error_response(rpc_id, 'ORDER_ALREADY_PAID')

        txn = PaymeTransaction.objects.create(
            order=order,
            payme_transaction_id=payme_id,
            payme_time=payme_time,
            state=PaymeTransaction.State.CREATED,
            amount=params['amount'],
        )

        return _ok_response(rpc_id, {
            'create_time': int(txn.create_time.timestamp() * 1000),
            'transaction': str(txn.pk),
            'state': txn.state,
        })

    # ── PerformTransaction ─────────────────────────────────────────────────────

    def _performTransaction(self, rpc_id, params: dict) -> dict:
        payme_id = params['id']
        txn = self._get_transaction(rpc_id, payme_id)
        if isinstance(txn, dict):
            return txn  # error response

        if txn.state == PaymeTransaction.State.PERFORMED:
            return _ok_response(rpc_id, {
                'transaction': str(txn.pk),
                'perform_time': int(txn.perform_time.timestamp() * 1000),
                'state': txn.state,
            })

        if txn.state != PaymeTransaction.State.CREATED:
            return _error_response(rpc_id, 'CANNOT_CANCEL_TRANSACTION')

        now = tz.now()
        txn.state = PaymeTransaction.State.PERFORMED
        txn.perform_time = now
        txn.save(update_fields=['state', 'perform_time'])

        # Mark order as paid
        order = txn.order
        order.payment_status = Order.PaymentStatus.PAID
        order.save(update_fields=['payment_status'])

        return _ok_response(rpc_id, {
            'transaction': str(txn.pk),
            'perform_time': int(now.timestamp() * 1000),
            'state': txn.state,
        })

    # ── CancelTransaction ──────────────────────────────────────────────────────

    def _cancelTransaction(self, rpc_id, params: dict) -> dict:
        payme_id = params['id']
        reason = params.get('reason', 10)
        txn = self._get_transaction(rpc_id, payme_id)
        if isinstance(txn, dict):
            return txn

        if txn.state in (PaymeTransaction.State.CANCELLED_BEFORE, PaymeTransaction.State.CANCELLED_AFTER):
            return _ok_response(rpc_id, {
                'transaction': str(txn.pk),
                'cancel_time': int(txn.cancel_time.timestamp() * 1000),
                'state': txn.state,
            })

        now = tz.now()
        if txn.state == PaymeTransaction.State.CREATED:
            txn.state = PaymeTransaction.State.CANCELLED_BEFORE
        elif txn.state == PaymeTransaction.State.PERFORMED:
            txn.state = PaymeTransaction.State.CANCELLED_AFTER
            # Refund: revert order payment
            txn.order.payment_status = Order.PaymentStatus.FAILED
            txn.order.save(update_fields=['payment_status'])
        else:
            return _error_response(rpc_id, 'CANNOT_CANCEL_TRANSACTION')

        txn.cancel_time = now
        txn.reason = reason
        txn.save(update_fields=['state', 'cancel_time', 'reason'])

        return _ok_response(rpc_id, {
            'transaction': str(txn.pk),
            'cancel_time': int(now.timestamp() * 1000),
            'state': txn.state,
        })

    # ── CheckTransaction ───────────────────────────────────────────────────────

    def _checkTransaction(self, rpc_id, params: dict) -> dict:
        payme_id = params['id']
        txn = self._get_transaction(rpc_id, payme_id)
        if isinstance(txn, dict):
            return txn

        return _ok_response(rpc_id, {
            'create_time': int(txn.create_time.timestamp() * 1000),
            'perform_time': int(txn.perform_time.timestamp() * 1000) if txn.perform_time else 0,
            'cancel_time': int(txn.cancel_time.timestamp() * 1000) if txn.cancel_time else 0,
            'transaction': str(txn.pk),
            'state': txn.state,
            'reason': txn.reason,
        })

    # ── GetStatement ───────────────────────────────────────────────────────────

    def _getStatement(self, rpc_id, params: dict) -> dict:
        from_ms = params.get('from', 0)
        to_ms = params.get('to', _now_ms())

        from_dt = datetime.fromtimestamp(from_ms / 1000, tz=timezone.utc)
        to_dt = datetime.fromtimestamp(to_ms / 1000, tz=timezone.utc)

        txns = PaymeTransaction.objects.filter(
            create_time__gte=from_dt,
            create_time__lte=to_dt,
        )

        transactions = []
        for txn in txns:
            transactions.append({
                'id': txn.payme_transaction_id,
                'time': txn.payme_time,
                'amount': txn.amount,
                'account': {'order_id': str(txn.order_id)},
                'create_time': int(txn.create_time.timestamp() * 1000),
                'perform_time': int(txn.perform_time.timestamp() * 1000) if txn.perform_time else 0,
                'cancel_time': int(txn.cancel_time.timestamp() * 1000) if txn.cancel_time else 0,
                'transaction': str(txn.pk),
                'state': txn.state,
                'reason': txn.reason,
            })

        return _ok_response(rpc_id, {'transactions': transactions})

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_order(self, rpc_id, params: dict):
        """Extract and validate order from params['account']['order_id']."""
        account = params.get('account', {})
        order_id = account.get('order_id')

        if not order_id:
            return None, _error_response(rpc_id, 'ORDER_NOT_FOUND')

        try:
            order = Order.objects.get(pk=int(order_id))
        except (Order.DoesNotExist, ValueError, TypeError):
            return None, _error_response(rpc_id, 'ORDER_NOT_FOUND')

        return order, None

    def _get_transaction(self, rpc_id, payme_id: str):
        """Fetch a PaymeTransaction by payme_transaction_id."""
        try:
            return PaymeTransaction.objects.select_related('order').get(
                payme_transaction_id=payme_id
            )
        except PaymeTransaction.DoesNotExist:
            return _error_response(rpc_id, 'TRANSACTION_NOT_FOUND')


# ─── Checkout URL builder ─────────────────────────────────────────────────────

def build_checkout_url(order: Order) -> str:
    """
    Build Payme checkout redirect URL.
    Format: {base_url}/{base64(m=MERCHANT_ID;ac.order_id=ORDER_ID;a=AMOUNT_TIYIN)}
    """
    merchant_id = settings.PAYME_MERCHANT_ID
    amount_tiyin = order.total * 100  # so'm → tiyin
    payload = f'm={merchant_id};ac.order_id={order.pk};a={amount_tiyin}'
    encoded = base64.b64encode(payload.encode()).decode()
    base_url = settings.PAYME_CHECKOUT_BASE_URL.rstrip('/')
    return f'{base_url}/{encoded}'


payme_handler = PaymeHandler()
