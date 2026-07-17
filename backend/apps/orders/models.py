from django.db import models
from apps.accounts.models import Address, TelegramUser
from apps.catalog.models import ProductVariant

class PromoCode(models.Model):
    """Promo code for discount."""
    code = models.CharField(max_length=50, unique=True, verbose_name="Kodi")
    discount_percent = models.PositiveSmallIntegerField(default=0, verbose_name="Chegirma foizi")
    discount_amount = models.PositiveIntegerField(default=0, verbose_name="Chegirma summasi")
    valid_until = models.DateTimeField(verbose_name="Amal qilish muddati")
    usage_limit = models.PositiveIntegerField(default=100, verbose_name="Ishlatilish limiti")
    times_used = models.PositiveIntegerField(default=0, verbose_name="Ishlatilgan soni")
    min_order_amount = models.PositiveIntegerField(default=0, verbose_name="Minimal buyurtma summasi")
    is_active = models.BooleanField(default=True, verbose_name="Faol")

    class Meta:
        verbose_name = "Promo-kod"
        verbose_name_plural = "Promo-kodlar"

    def __str__(self):
        return f"{self.code} (-{self.discount_percent}% / -{self.discount_amount} so'm)"

    def is_valid(self, order_amount=0):
        from django.utils import timezone
        if not self.is_active:
            return False
        if timezone.now() > self.valid_until:
            return False
        if self.times_used >= self.usage_limit:
            return False
        if order_amount < self.min_order_amount:
            return False
        return True

    def calculate_discount(self, order_amount):
        if self.discount_percent > 0:
            return int(order_amount * self.discount_percent / 100)
        return min(self.discount_amount, order_amount)


class DeliveryTimeSlot(models.Model):
    """Delivery time slots configuration."""
    label = models.CharField(max_length=100, verbose_name="Vaqt oralig'i (matn)")
    date = models.DateField(verbose_name="Sana")
    start_time = models.TimeField(verbose_name="Boshlanish vaqti")
    end_time = models.TimeField(verbose_name="Tugash vaqti")
    max_orders = models.PositiveSmallIntegerField(default=20, verbose_name="Maksimal buyurtmalar")
    is_active = models.BooleanField(default=True, verbose_name="Faol")

    class Meta:
        verbose_name = "Yetkazib berish vaqti"
        verbose_name_plural = "Yetkazib berish vaqtlari"
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"{self.date}: {self.label} (max: {self.max_orders})"


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
    delivery_time_slot = models.ForeignKey(
        DeliveryTimeSlot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='Yetkazish vaqti'
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
    promo_code = models.ForeignKey(
        'PromoCode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='Promo-kod'
    )
    discount_amount = models.PositiveIntegerField(default=0, verbose_name='Chegirma summasi')
    delivery_fee = models.PositiveIntegerField(default=0, verbose_name='Yetkazish narxi')
    total = models.PositiveIntegerField(default=0, verbose_name='Jami summa')
    comment = models.TextField(blank=True, verbose_name='Izoh')
    courier = models.ForeignKey(
        'accounts.Courier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='Kuryer'
    )
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
    bundle = models.ForeignKey(
        'catalog.ProductBundle',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items',
        verbose_name='To\'plam',
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


class FeedbackRequest(models.Model):
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='feedback_request',
        verbose_name='Buyurtma'
    )
    scheduled_time = models.DateTimeField(verbose_name='Rejalashtirilgan vaqt')
    is_sent = models.BooleanField(default=False, verbose_name='Yuborildimi')
    rating = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name='Baholash (1-5)')
    comment = models.TextField(blank=True, verbose_name='Fikr-mulohaza')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Fikr-mulohaza so'rovi"
        verbose_name_plural = "Fikr-mulohaza so'rovlari"

    def __str__(self):
        return f"Order #{self.order_id} Feedback"


class CorporateInquiry(models.Model):
    """An inquiry from a corporate/wholesale customer."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Kutilmoqda'
        PROCESSED = 'processed', 'Bajarildi'
        CANCELLED = 'cancelled', 'Bekor qilindi'

    company_name = models.CharField(max_length=255, verbose_name="Kompaniya / Tashkilot nomi")
    contact_person = models.CharField(max_length=150, verbose_name="Aloqachi shaxs")
    phone = models.CharField(max_length=50, verbose_name="Telefon raqami")
    estimated_quantity = models.PositiveIntegerField(default=1, verbose_name="Taxminiy soni")
    comment = models.TextField(blank=True, verbose_name="Izoh / Qo'shimcha ma'lumotlar")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Holat"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yuborilgan vaqt")

    class Meta:
        verbose_name = "Korporativ so'rov"
        verbose_name_plural = "Korporativ so'rovlar"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.company_name} — {self.contact_person}"
