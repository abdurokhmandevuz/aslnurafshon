"""
Catalog application models.

Category      — product categories with emoji icon and display order
Product       — tea/coffee products with discount, featured flags
ProductVariant — weight/size variants with individual prices and stock
"""
from django.db import models
from django.core.validators import MaxValueValidator
from django.utils.text import slugify
from django.utils import timezone
from datetime import timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver
import threading
import os

# Allow Django ORM operations inside async loops in background threads
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


class Banner(models.Model):
    """Home page promotional banners."""

    title = models.CharField(max_length=255, verbose_name='Sarlavha')
    subtitle = models.CharField(max_length=255, blank=True, verbose_name='Kichik matn')
    image = models.ImageField(upload_to='banners/', verbose_name='Rasm')
    button_text = models.CharField(max_length=50, default="Batafsil", verbose_name="Tugma matni")
    link_url = models.CharField(max_length=255, blank=True, verbose_name="Havola (URL)")
    order = models.PositiveSmallIntegerField(default=0, verbose_name='Tartib raqami')
    is_active = models.BooleanField(default=True, verbose_name='Faol')
    starts_at = models.DateTimeField(null=True, blank=True, verbose_name="Boshlanish vaqti")
    ends_at = models.DateTimeField(null=True, blank=True, verbose_name="Tugash vaqti")

    class Meta:
        verbose_name = 'Banner'
        verbose_name_plural = 'Bannerlar'
        ordering = ['order', '-id']

    def __str__(self):
        return self.title


class Category(models.Model):
    """Product category (e.g. "Ko'k choy", "Kofe", "Aksessuarlar")."""

    name = models.CharField(max_length=100, verbose_name='Nomi')
    slug = models.SlugField(max_length=120, unique=True, blank=True, verbose_name='Slug')
    icon_emoji = models.CharField(
        max_length=10, blank=True, default='🍵', verbose_name='Emoji belgisi'
    )
    image = models.ImageField(
        upload_to='categories/', null=True, blank=True, verbose_name='Rasm'
    )
    order = models.PositiveSmallIntegerField(default=0, verbose_name='Tartib raqami')
    is_active = models.BooleanField(default=True, verbose_name='Faol')

    class Meta:
        verbose_name = 'Kategoriya'
        verbose_name_plural = 'Kategoriyalar'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class Product(models.Model):
    """A product in the catalog."""

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name='Kategoriya',
    )
    name = models.CharField(max_length=200, verbose_name='Nomi')
    description = models.TextField(blank=True, verbose_name='Tavsif')
    image = models.ImageField(
        upload_to='products/', null=True, blank=True, verbose_name='Rasm'
    )
    is_featured = models.BooleanField(default=False, verbose_name='Tavsiya etilgan')
    is_new = models.BooleanField(default=False, verbose_name='Yangi')
    is_popular = models.BooleanField(default=False, verbose_name='Mashhur')
    discount_percent = models.PositiveSmallIntegerField(
        default=0, validators=[MaxValueValidator(99)], verbose_name='Chegirma (%)'
    )
    is_active = models.BooleanField(default=True, verbose_name='Faol')
    created_at = models.DateTimeField(auto_now_add=True)
    related_products = models.ManyToManyField('self', blank=True, symmetrical=False, related_name='related_to', verbose_name="O'xshash mahsulotlar")

    class Meta:
        verbose_name = 'Mahsulot'
        verbose_name_plural = 'Mahsulotlar'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def min_price(self):
        """Minimum variant price (for listing display)."""
        variant = self.variants.filter(is_available=True).order_by('price').first()
        return variant.price if variant else None

    @property
    def discounted_min_price(self):
        """min_price after applying discount_percent."""
        p = self.min_price
        if p is None:
            return None
        if self.discount_percent:
            return int(p * (100 - self.discount_percent) / 100)
        return p

    @property
    def average_rating(self):
        avg = self.reviews.aggregate(models.Avg('rating'))['rating__avg']
        return round(avg, 1) if avg is not None else None

    @property
    def reviews_count(self):
        return self.reviews.count()


class ProductVariant(models.Model):
    """A generalized variant of a Product with its own price and stock."""

    class VariantType(models.TextChoices):
        SHT = 'sht', 'SHT'
        GR = 'gr', 'GR'
        KG = 'kg', 'KG'

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name='Mahsulot',
    )
    label = models.CharField(
        max_length=100, verbose_name="Variant nomi", help_text="Masalan: 100g, 25 dona, Olma ta'mli"
    )
    variant_type = models.CharField(
        max_length=20,
        choices=VariantType.choices,
        default=VariantType.SHT,
        verbose_name="Variant turi"
    )
    price = models.PositiveIntegerField(verbose_name="Narxi (so'm)")
    stock_qty = models.PositiveIntegerField(default=0, verbose_name='Ombordagi miqdor')
    is_available = models.BooleanField(default=True, verbose_name='Mavjud')
    is_default = models.BooleanField(default=False, verbose_name='Asosiy variant', help_text="Mahsulot ochilganda avtomatik tanlanadi")
    order = models.PositiveSmallIntegerField(default=0, verbose_name='Tartib raqami')
    last_low_stock_notified = models.DateTimeField(null=True, blank=True, verbose_name="Oxirgi ogohlantirish vaqti")
    barcode = models.CharField(max_length=100, blank=True, null=True, unique=True, verbose_name="Shtrix kod")

    class Meta:
        verbose_name = 'Mahsulot varianti'
        verbose_name_plural = 'Mahsulot variantlari'
        ordering = ['order', 'price']

    def __str__(self):
        return f"{self.product.name} — {self.label} ({self.price} so'm)"

    def save(self, *args, **kwargs):
        if self.stock_qty <= 0:
            self.is_available = False
        if self.stock_qty > 3:
            self.last_low_stock_notified = None
        super().save(*args, **kwargs)


class FavoriteProduct(models.Model):
    """Product marked as favorite by a TelegramUser."""

    user = models.ForeignKey(
        'accounts.TelegramUser',
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Foydalanuvchi',
    )
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='favorited_by',
        verbose_name='Mahsulot',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Sevimli mahsulot'
        verbose_name_plural = 'Sevimli mahsulotlar'
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user} — {self.product.name}"


class DailyDeal(models.Model):
    """Daily deal configuration (one active variant per day)."""

    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, verbose_name="Mahsulot varianti")
    discount_percent = models.PositiveSmallIntegerField(
        default=0, validators=[MaxValueValidator(99)], verbose_name="Chegirma (%)"
    )
    date = models.DateField(unique=True, verbose_name="Sana")
    starts_at = models.DateTimeField(default=timezone.now, verbose_name="Boshlanish vaqti")
    is_active = models.BooleanField(default=True, verbose_name="Faol")

    class Meta:
        verbose_name = "Kunlik taklif"
        verbose_name_plural = "Kunlik takliflar"
        ordering = ['-date']

    def __str__(self):
        return f"{self.date}: {self.variant} (-{self.discount_percent}%)"

    @property
    def deal_price(self):
        """Price of the variant after daily deal discount."""
        p = self.variant.price
        if self.discount_percent:
            return int(p * (100 - self.discount_percent) / 100)
        return p

    @property
    def expires_at(self):
        return self.starts_at + timedelta(hours=24)


class ProductReview(models.Model):
    """Product review submitted by a TelegramUser."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews', verbose_name='Mahsulot')
    user = models.ForeignKey('accounts.TelegramUser', on_delete=models.CASCADE, related_name='reviews', verbose_name='Foydalanuvchi')
    rating = models.PositiveSmallIntegerField(verbose_name='Baho (1-5)')
    comment = models.TextField(blank=True, verbose_name='Sharh')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Mahsulot sharhi'
        verbose_name_plural = 'Mahsulot sharhlari'
        unique_together = ('product', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.product.name} ({self.rating}/5)"


class ProductBundle(models.Model):
    name = models.CharField(max_length=255, verbose_name="To'plam nomi")
    slug = models.SlugField(unique=True, verbose_name="Slug")
    description = models.TextField(blank=True, verbose_name="Tavsifi")
    image = models.ImageField(upload_to='bundles/', verbose_name="To'plam rasmi")
    discount_percent = models.PositiveSmallIntegerField(
        default=0, validators=[MaxValueValidator(99)], verbose_name="Chegirma foizi"
    )
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqt")

    class Meta:
        verbose_name = "To'plam (Combo)"
        verbose_name_plural = "To'plamlar (Combo)"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} (-{self.discount_percent}%)"

    @property
    def original_price(self):
        return sum(item.variant.price * item.quantity for item in self.items.all())

    @property
    def price(self):
        orig = self.original_price
        return int(orig * (100 - self.discount_percent) / 100)


class BundleItem(models.Model):
    bundle = models.ForeignKey(ProductBundle, on_delete=models.CASCADE, related_name='items', verbose_name="To'plam")
    variant = models.ForeignKey('ProductVariant', on_delete=models.CASCADE, related_name='bundle_items', verbose_name="Variant")
    quantity = models.PositiveSmallIntegerField(default=1, verbose_name="Soni")

    class Meta:
        verbose_name = "To'plam elementi"
        verbose_name_plural = "To'plam elementlari"

    def __str__(self):
        return f"{self.variant.product.name} ({self.variant.label}) x {self.quantity}"


def _fire_in_thread(fn, *args, **kwargs):
    t = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    t.start()

def _run_low_stock_notification(variant_id):
    try:
        import asyncio
        from bot.notifications import notify_low_stock
        asyncio.run(notify_low_stock(variant_id))
    except Exception:
        pass

@receiver(post_save, sender=ProductVariant)
def track_low_stock(sender, instance, **kwargs):
    if instance.stock_qty <= 3 and not instance.last_low_stock_notified:
        # Use update to avoid triggering infinite signal recursion
        ProductVariant.objects.filter(id=instance.id).update(last_low_stock_notified=timezone.now())
        _fire_in_thread(_run_low_stock_notification, instance.id)
