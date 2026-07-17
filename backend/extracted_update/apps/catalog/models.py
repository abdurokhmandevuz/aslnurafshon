"""
Catalog application models.

Category      — product categories with emoji icon and display order
Product       — tea/coffee products with discount, featured flags
ProductVariant — weight/size variants with individual prices and stock
"""
from django.db import models
from django.utils.text import slugify


class Banner(models.Model):
    """Home page promotional banners."""

    title = models.CharField(max_length=200, verbose_name='Sarlavha')
    subtitle = models.CharField(max_length=200, blank=True, verbose_name='Kichik matn')
    image = models.ImageField(upload_to='banners/', verbose_name='Rasm')
    is_active = models.BooleanField(default=True, verbose_name='Faol')
    order = models.PositiveSmallIntegerField(default=0, verbose_name='Tartib raqami')

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
        default=0, verbose_name='Chegirma (%)'
    )
    is_active = models.BooleanField(default=True, verbose_name='Faol')
    created_at = models.DateTimeField(auto_now_add=True)

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


class ProductVariant(models.Model):
    """A generalized variant of a Product with its own price and stock."""

    class VariantType(models.TextChoices):
        WEIGHT = 'weight', 'Og\'irlik'
        PIECE = 'piece', 'Dona'
        FLAVOR = 'flavor', 'Ta\'m'
        VOLUME = 'volume', 'Hajm'

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
        default=VariantType.WEIGHT,
        verbose_name="Variant turi"
    )
    price = models.PositiveIntegerField(verbose_name="Narxi (so'm)")
    stock_qty = models.PositiveIntegerField(default=0, verbose_name='Ombordagi miqdor')
    is_available = models.BooleanField(default=True, verbose_name='Mavjud')
    is_default = models.BooleanField(default=False, verbose_name='Asosiy variant', help_text="Mahsulot ochilganda avtomatik tanlanadi")
    order = models.PositiveSmallIntegerField(default=0, verbose_name='Tartib raqami')

    class Meta:
        verbose_name = 'Mahsulot varianti'
        verbose_name_plural = 'Mahsulot variantlari'
        ordering = ['order', 'price']

    def __str__(self):
        return f"{self.product.name} — {self.label} ({self.price} so'm)"
