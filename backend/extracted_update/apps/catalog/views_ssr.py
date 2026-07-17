from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Min, Q
from .models import Category, Product, Banner

def catalog_view(request):
    banners = Banner.objects.filter(is_active=True).order_by('order', '-id')
    categories = Category.objects.filter(is_active=True).annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).order_by('order', 'name')
    
    base_products = Product.objects.filter(is_active=True).select_related('category').prefetch_related('variants').annotate(min_price_val=Min('variants__price'))
    
    popular_products = base_products.filter(is_popular=True)[:10]
    new_products = base_products.filter(is_new=True)[:10]

    category_id = request.GET.get('category')
    if category_id:
        products = base_products.filter(category_id=category_id)
    else:
        products = base_products

    context = {
        'banners': banners,
        'categories': categories,
        'products': products,
        'popular_products': popular_products,
        'new_products': new_products,
    }
    return render(request, 'katalog.html', context)

def product_detail_view(request, pk):
    base_products = Product.objects.filter(is_active=True).select_related('category').prefetch_related('variants').annotate(min_price_val=Min('variants__price'))
    product = get_object_or_404(base_products, pk=pk)
    
    context = {
        'product': product,
    }
    return render(request, 'mahsulot.html', context)
