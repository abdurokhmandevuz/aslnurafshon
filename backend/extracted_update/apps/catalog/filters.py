"""django-filter FilterSet for catalog products."""
import django_filters

from .models import Product


class ProductFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name='category__slug', lookup_expr='exact')
    min_price = django_filters.NumberFilter(method='filter_min_price')
    max_price = django_filters.NumberFilter(method='filter_max_price')
    is_featured = django_filters.BooleanFilter()
    is_new = django_filters.BooleanFilter()

    class Meta:
        model = Product
        fields = ['category', 'is_featured', 'is_new']

    def filter_min_price(self, queryset, name, value):
        return queryset.filter(variants__price__gte=value).distinct()

    def filter_max_price(self, queryset, name, value):
        return queryset.filter(variants__price__lte=value).distinct()
