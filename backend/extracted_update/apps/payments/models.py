"""
Payments application models.

PaymeTransaction  — tracks Payme Merchant API transactions (JSON-RPC state machine)
ClickTransaction  — tracks Click Merchant API prepare/complete flow
"""
from django.db import models

from apps.orders.models import Order


class PaymeTransaction(models.Model):
    """
    Payme Merchant API transaction.
    State machine:
        1  = CREATED   (CreateTransaction called)
        2  = PERFORMED (PerformTransaction called)
       -1  = CANCELLED before payment
       -2  = CANCELLED after payment
    """

    class State(models.IntegerChoices):
        CREATED = 1, 'Yaratildi'
        PERFORMED = 2, 'Amalga oshirildi'
        CANCELLED_BEFORE = -1, "Bekor qilindi (to'lovdan oldin)"
        CANCELLED_AFTER = -2, "Bekor qilindi (to'lovdan keyin)"

    class CancelReason(models.IntegerChoices):
        RECEIVER_NOT_FOUND = 1, 'Qabul qiluvchi topilmadi'
        PROCESSING_EXECUTION_FAILED = 2, 'Bajarish muammosi'
        EXECUTION_FAILED = 3, 'Xatolik'
        CANCELLED_BY_TIMEOUT = 4, 'Vaqt tugadi'
        FUND_RETURNED = 5, 'Qaytarildi'
        UNKNOWN = 10, "Noma'lum"

    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name='payme_transactions',
        verbose_name='Buyurtma',
    )
    payme_transaction_id = models.CharField(
        max_length=255, unique=True, verbose_name='Payme transaction ID'
    )
    payme_time = models.BigIntegerField(
        help_text='Transaction create time from Payme (Unix ms)'
    )
    state = models.SmallIntegerField(
        choices=State.choices, default=State.CREATED, verbose_name='Holat'
    )
    amount = models.BigIntegerField(verbose_name='Summa (tiyin)')
    reason = models.SmallIntegerField(
        null=True, blank=True,
        choices=CancelReason.choices,
        verbose_name='Bekor qilish sababi',
    )
    create_time = models.DateTimeField(auto_now_add=True)
    perform_time = models.DateTimeField(null=True, blank=True, verbose_name='Amalga oshirilgan vaqt')
    cancel_time = models.DateTimeField(null=True, blank=True, verbose_name='Bekor qilingan vaqt')

    class Meta:
        verbose_name = 'Payme tranzaksiya'
        verbose_name_plural = 'Payme tranzaksiyalar'

    def __str__(self):
        return f'Payme #{self.payme_transaction_id} order={self.order_id}'


class ClickTransaction(models.Model):
    """Click Merchant API transaction (Prepare → Complete flow)."""

    class Status(models.IntegerChoices):
        WAITING = 0, 'Kutilmoqda'
        CONFIRMED = 1, 'Tasdiqlandi'
        CANCELLED = -1, 'Bekor qilindi'
        ALREADY_PAID = -2, "Allaqachon to'langan"

    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name='click_transactions',
        verbose_name='Buyurtma',
    )
    click_trans_id = models.BigIntegerField(verbose_name='Click trans ID', db_index=True)
    click_paydoc_id = models.BigIntegerField(null=True, blank=True, verbose_name='Click paydoc ID')
    merchant_trans_id = models.CharField(
        max_length=255, verbose_name='Merchant trans ID (order_id)'
    )
    status = models.SmallIntegerField(
        choices=Status.choices, default=Status.WAITING, verbose_name='Holat'
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Summa')
    sign_time = models.CharField(max_length=20, verbose_name='Sign time')
    error = models.SmallIntegerField(default=0, verbose_name='Xato kodi')
    error_note = models.CharField(max_length=255, blank=True, verbose_name='Xato matni')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Click tranzaksiya'
        verbose_name_plural = 'Click tranzaksiyalar'

    def __str__(self):
        return f'Click #{self.click_trans_id} order={self.order_id}'
