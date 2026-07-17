"""Views for catalog app."""
from django.db.models import Count, Min, Q

from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .filters import ProductFilter
from .models import Category, Product, Banner
from .serializers import CategorySerializer, ProductDetailSerializer, ProductListSerializer, BannerSerializer


class HomeAPIView(APIView):
    """GET /api/catalog/home/ — returns banners, categories, popular and new products."""
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        banners = Banner.objects.filter(is_active=True).order_by('order', '-id')
        categories = Category.objects.filter(is_active=True).annotate(
            product_count=Count('products', filter=Q(products__is_active=True))
        ).order_by('order', 'name')
        
        # Optimize products queries
        base_products = Product.objects.filter(is_active=True).select_related('category').prefetch_related('variants').annotate(min_price_val=Min('variants__price'))
        
        popular_products = base_products.filter(is_popular=True)[:10]
        new_products = base_products.filter(is_new=True)[:10]

        return Response({
            'banners': BannerSerializer(banners, many=True, context={'request': request}).data,
            'categories': CategorySerializer(categories, many=True, context={'request': request}).data,
            'popular_products': ProductListSerializer(popular_products, many=True, context={'request': request}).data,
            'new_products': ProductListSerializer(new_products, many=True, context={'request': request}).data,
        })


class CategoryListView(generics.ListAPIView):
    """GET /api/categories/ — list all active categories with product count."""

    serializer_class = CategorySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return (
            Category.objects.filter(is_active=True)
            .annotate(product_count=Count('products', filter=Q(products__is_active=True)))
            .order_by('order', 'name')
        )


class ProductListView(generics.ListAPIView):
    """
    GET /api/products/

    Query params:
        category  — category slug
        search    — searches in name, description
        ordering  — price | -price | -created_at | name
        is_featured, is_new — boolean filters
        min_price, max_price
    """

    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]
    filterset_class = ProductFilter
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = (
            Product.objects.filter(is_active=True)
            .select_related('category')
            .prefetch_related('variants')
            .annotate(min_price_val=Min('variants__price'))
        )
        return qs

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        return ctx


class ProductDetailView(generics.RetrieveAPIView):
    """GET /api/products/<id>/"""

    serializer_class = ProductDetailSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return (
            Product.objects.filter(is_active=True)
            .select_related('category')
            .prefetch_related('variants')
        )
