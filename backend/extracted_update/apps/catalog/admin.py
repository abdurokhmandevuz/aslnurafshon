"""Django admin configuration for catalog app."""
from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Product, ProductVariant, Banner

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('title',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('icon_emoji', 'name', 'slug', 'order', 'is_active', 'product_count')
    list_editable = ('order', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    ordering = ('order',)

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Mahsulotlar soni'


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ('label', 'variant_type', 'price', 'stock_qty', 'is_available', 'is_default', 'order')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'thumbnail', 'name', 'category', 'price_range',
        'is_featured', 'is_new', 'is_active', 'total_stock',
    )
    list_filter = ('category', 'is_featured', 'is_new', 'is_popular', 'is_active')
    list_editable = ('is_featured', 'is_new', 'is_active')
    search_fields = ('name', 'description')
    inlines = [ProductVariantInline]
    readonly_fields = ('created_at',)

    def thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="40" height="40" style="object-fit:cover;border-radius:6px"/>', obj.image.url)
        return '—'
    thumbnail.short_description = 'Rasm'

    def price_range(self, obj):
        variants = obj.variants.all()
        if not variants: return '-'
        prices = [v.price for v in variants]
        if len(set(prices)) > 1:
            return f"{min(prices):,.0f} - {max(prices):,.0f} so'm"
        return f"{prices[0]:,.0f} so'm"
    price_range.short_description = 'Narx'

    def total_stock(self, obj):
        return sum(v.stock_qty for v in obj.variants.all())
    total_stock.short_description = 'Jami omborda'


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('product', 'label', 'variant_type', 'price', 'stock_qty', 'is_available', 'is_default')
    list_filter = ('is_available', 'variant_type', 'is_default')
    list_editable = ('price', 'stock_qty', 'is_available', 'is_default')
    search_fields = ('product__name', 'label')
    raw_id_fields = ('product',)
