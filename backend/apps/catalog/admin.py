"""Django admin configuration for catalog app."""
from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Category, Product, ProductVariant, Banner, FavoriteProduct,
    DailyDeal, ProductReview, ProductBundle, BundleItem
)

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'is_active', 'button_text', 'starts_at', 'ends_at')
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
    fields = ('label', 'variant_type', 'price', 'stock_qty', 'barcode', 'is_available', 'is_default', 'order')


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

    class Media:
        css = {
            'all': ('admin/catalog/product_scanner.css',)
        }
        js = ('admin/catalog/product_scanner.js',)

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('barcode-lookup/', self.admin_site.admin_view(self.barcode_lookup_view), name='catalog_product_barcode_lookup'),
        ]
        return custom_urls + urls

    def barcode_lookup_view(self, request):
        from django.http import JsonResponse
        from django.urls import reverse
        from apps.catalog.models import ProductVariant
        
        barcode = request.GET.get('barcode', '').strip()
        if not barcode:
            return JsonResponse({'exists': False, 'message': 'Shtrix kod yuborilmadi'}, status=400)
            
        try:
            variant = ProductVariant.objects.select_related('product').get(barcode=barcode)
            product_admin_url = reverse('admin:catalog_product_change', args=[variant.product.id])
            return JsonResponse({
                'exists': True,
                'product_name': variant.product.name,
                'label': variant.label,
                'barcode': variant.barcode,
                'product_admin_url': product_admin_url,
                'message': 'Mavjud mahsulot topildi. Tahrirlash uchun havolani bosing.'
            })
        except ProductVariant.DoesNotExist:
            # Fallback: Query Open Food Facts API
            import urllib.request
            import json
            
            off_url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
            try:
                req = urllib.request.Request(off_url, headers={'User-Agent': 'AslNurafshon/1.0'})
                with urllib.request.urlopen(req, timeout=2) as response:
                    res_data = json.loads(response.read().decode())
                    if res_data.get('status') == 1:
                        product_data = res_data.get('product', {})
                        product_name = None
                        for key in ['product_name_uz', 'product_name_ru', 'product_name', 'product_name_en']:
                            val = product_data.get(key)
                            if val:
                                product_name = val
                                break
                        
                        quantity = product_data.get('quantity', '')
                        brands = product_data.get('brands', '')
                        label_parts = []
                        if brands:
                            label_parts.append(brands)
                        if quantity:
                            label_parts.append(quantity)
                        label = " ".join(label_parts) if label_parts else "1 ta"
                        
                        return JsonResponse({
                            'exists': False,
                            'product_name': product_name,
                            'label': label,
                            'barcode': barcode,
                            'message': f"Shtrix kod tizimdan topildi: {product_name}. Ma'lumotlar to'ldirildi."
                        })
            except Exception:
                pass

            return JsonResponse({
                'exists': False,
                'message': 'Shtrix kod topilmadi. Qolgan maydonlarni o\'zingiz to\'ldirishingiz mumkin.'
            })

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
    list_display = ('product', 'label', 'variant_type', 'price', 'stock_qty', 'barcode', 'is_available', 'is_default')
    list_filter = ('is_available', 'variant_type', 'is_default')
    list_editable = ('price', 'stock_qty', 'is_available', 'is_default')
    search_fields = ('product__name', 'label', 'barcode')
    raw_id_fields = ('product',)


@admin.register(FavoriteProduct)
class FavoriteProductAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    search_fields = ('user__full_name', 'product__name')


@admin.register(DailyDeal)
class DailyDealAdmin(admin.ModelAdmin):
    list_display = ('date', 'variant', 'discount_percent', 'deal_price', 'is_active')
    list_editable = ('discount_percent', 'is_active')
    list_filter = ('is_active', 'date')
    search_fields = ('variant__product__name', 'variant__label')


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('product__name', 'user__full_name', 'comment')


class BundleItemInline(admin.TabularInline):
    model = BundleItem
    extra = 1


@admin.register(ProductBundle)
class ProductBundleAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'discount_percent', 'original_price', 'price', 'is_active')
    list_editable = ('is_active',)
    prepopulated_fields = {'slug': ('name',)}
    inlines = [BundleItemInline]
