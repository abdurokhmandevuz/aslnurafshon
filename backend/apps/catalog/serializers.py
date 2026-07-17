"""Serializers for catalog app."""
from rest_framework import serializers

from .models import Category, Product, ProductVariant, Banner


class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = ['id', 'title', 'subtitle', 'image']


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'icon_emoji', 'image', 'order', 'product_count']


class ProductVariantSerializer(serializers.ModelSerializer):
    """
    Variant uchun serializer.
    Chegirma hisoblangan maxsus narxni ham qo'shib beradi.
    """
    discounted_price = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = ['id', 'label', 'variant_type', 'price', 'discounted_price', 'stock_qty', 'is_available', 'is_default', 'order']

    def get_discounted_price(self, variant):
        product = variant.product
        if product.discount_percent:
            return int(variant.price * (100 - product.discount_percent) / 100)
        return variant.price


class ProductListSerializer(serializers.ModelSerializer):
    """Compact representation for product listing."""

    category_name = serializers.CharField(source='category.name', read_only=True)
    min_price = serializers.IntegerField(read_only=True)
    discounted_min_price = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'image', 'category_name',
            'is_featured', 'is_new', 'discount_percent',
            'min_price', 'discounted_min_price', 'is_active',
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    """Full product detail including all variants."""

    category = CategorySerializer(read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    min_price = serializers.IntegerField(read_only=True)
    discounted_min_price = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'image', 'category',
            'is_featured', 'is_new', 'discount_percent',
            'min_price', 'discounted_min_price',
            'variants', 'is_active', 'created_at',
        ]
