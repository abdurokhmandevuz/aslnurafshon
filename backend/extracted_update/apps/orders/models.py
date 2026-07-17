"""
Orders application models.

Order     — customer order with status tracking, delivery info, payment
OrderItem — individual product variant line item with price snapshot
"""
from django.db import models

from apps.accounts.models import Address, TelegramUser
from apps.catalog.models import ProductVariant


class Order(models.Model):
    """A customer purchase order."""

    class Status(models.TextChoices):
        NEW = 'yangi', 'Yangi'
        PREPARING = 'tayyorlanmoqda', 'Tayyorlanmoqda'
        ON_THE_WAY = 'yolda', "Yo'lda"
        DELIVERED = 'yetkazildi', 'Yetkazildi'
        CANCELLED = 'bekor_qilindi', 'Bekor qilindi'

    class DeliveryType(models.TextChoices):
        DELIVERY = 'yetkazib_berish', 'Yetkazib berish'
        PICKUP = 'olib_ketish', 'Olib ketish'

    class PaymentMethod(models.TextChoices):
        PAYME = 'payme', 'Payme'
        CLICK = 'click', 'Click'
        CASH = 'naqd', 'Naqd pul'

    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Kutilmoqda'
        PAID = 'paid', "To'langan"
        FAILED = 'failed', 'Xatolik'

    user = models.ForeignKey(
        TelegramUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='orders',
        verbose_name='Foydalanuvchi',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        verbose_name='Holat',
    )
    delivery_type = models.CharField(
        max_length=20,
        choices=DeliveryType.choices,
        default=DeliveryType.DELIVERY,
        verbose_name='Yetkazish turi',
    )
    address = models.ForeignKey(
        Address,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='Manzil',
    )
    delivery_time_slot = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Yetkazish vaqti',
        help_text='Masalan: 14:00–16:00',
    )
    payment_method = models.CharField(
        max_length=10,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
        verbose_name="To'lov usuli",
    )
    payment_status = models.CharField(
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name="To'lov holati",
    )
    subtotal = models.PositiveIntegerField(default=0, verbose_name='Mahsulotlar summasi')
    delivery_fee = models.PositiveIntegerField(default=0, verbose_name='Yetkazish narxi')
    total = models.PositiveIntegerField(default=0, verbose_name='Jami summa')
    comment = models.TextField(blank=True, verbose_name='Izoh')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Buyurtma'
        verbose_name_plural = 'Buyurtmalar'
        ordering = ['-created_at']

    def __str__(self):
        return f'Buyurtma #{self.pk} — {self.user}'

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())


class OrderItem(models.Model):
    """A single product-variant line in an order."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Buyurtma',
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.SET_NULL,
        null=True,
        related_name='order_items',
        verbose_name='Variant',
    )
    product_name_snapshot = models.CharField(
        max_length=250,
        verbose_name='Mahsulot nomi (snapshot)',
        help_text='Saved at order time to preserve history',
    )
    variant_weight_snapshot = models.CharField(
        max_length=50,
        verbose_name="Variant og'irligi (snapshot)",
        blank=True,
    )
    quantity = models.PositiveSmallIntegerField(default=1, verbose_name='Miqdor')
    price_at_order = models.PositiveIntegerField(verbose_name='Narx (buyurtma vaqtida)')

    class Meta:
        verbose_name = 'Buyurtma elementi'
        verbose_name_plural = 'Buyurtma elementlari'

    def __str__(self):
        return f'{self.product_name_snapshot} × {self.quantity}'

    @property
    def line_total(self):
        return self.quantity * self.price_at_order
