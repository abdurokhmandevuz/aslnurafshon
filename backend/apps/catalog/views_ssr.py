from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Min, Q
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
import json
from .models import (
    Banner,
    Category,
    DailyDeal,
    FavoriteProduct,
    Product,
    ProductBundle,
    ProductReview,
    ProductVariant,
)
from apps.orders.views_ssr import get_or_auth_user

def catalog_view(request):
    now = timezone.now()
    banners = Banner.objects.filter(
        is_active=True
    ).filter(
        Q(starts_at__isnull=True) | Q(starts_at__lte=now)
    ).filter(
        Q(ends_at__isnull=True) | Q(ends_at__gte=now)
    ).order_by('order', '-id')
    
    categories = Category.objects.filter(is_active=True).annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).order_by('order', 'name')
    
    base_products = Product.objects.filter(is_active=True).select_related('category').prefetch_related('variants').annotate(min_price_val=Min('variants__price'))
    
    popular_products = base_products.filter(is_popular=True)[:10]
    new_products = base_products.filter(is_new=True)[:10]

    category_id = request.GET.get('category')
    is_bundle_category = False
    bundles = []
    
    if category_id:
        try:
            category = Category.objects.get(id=category_id)
            if category.slug == 'toplamlar' or category.name == "To'plamlar":
                is_bundle_category = True
                bundles = ProductBundle.objects.filter(is_active=True).prefetch_related('items__variant__product')
                products = Product.objects.none()
            else:
                products = base_products.filter(category_id=category_id)
        except Category.DoesNotExist:
            products = base_products
    else:
        products = base_products

    query = request.GET.get('q')
    if query:
        if is_bundle_category:
            bundles = bundles.filter(name__icontains=query)
        else:
            products = products.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )

    # Load favorites
    user = get_or_auth_user(request)
    favorite_product_ids = []
    if user:
        favorite_product_ids = list(user.favorites.values_list('product_id', flat=True))

    # Today's deal
    today = timezone.localdate()
    daily_deal = DailyDeal.objects.filter(is_active=True, date=today).select_related('variant__product').first()

    context = {
        'banners': banners,
        'categories': categories,
        'products': products,
        'bundles': bundles,
        'is_bundle_category': is_bundle_category,
        'popular_products': popular_products,
        'new_products': new_products,
        'favorite_product_ids': favorite_product_ids,
        'daily_deal': daily_deal,
    }
    return render(request, 'katalog.html', context)


def promotions_view(request):
    """Show only active, admin-managed promotional content."""
    now = timezone.now()
    banners = Banner.objects.filter(
        is_active=True
    ).filter(
        Q(starts_at__isnull=True) | Q(starts_at__lte=now)
    ).filter(
        Q(ends_at__isnull=True) | Q(ends_at__gte=now)
    ).order_by('order', '-id')

    discount_products = (
        Product.objects.filter(is_active=True, discount_percent__gt=0)
        .prefetch_related('variants')
        .order_by('-discount_percent', '-created_at')
    )
    bundles = (
        ProductBundle.objects.filter(is_active=True, discount_percent__gt=0)
        .prefetch_related('items__variant__product')
        .order_by('-discount_percent', '-created_at')
    )
    daily_deal = (
        DailyDeal.objects.filter(is_active=True, date=timezone.localdate())
        .select_related('variant__product')
        .first()
    )
    return render(request, 'aksiyalar.html', {
        'banners': banners,
        'discount_products': discount_products,
        'bundles': bundles,
        'daily_deal': daily_deal,
    })

def product_detail_view(request, pk):
    base_products = Product.objects.filter(is_active=True).select_related('category').prefetch_related('variants').annotate(min_price_val=Min('variants__price'))
    product = get_object_or_404(base_products, pk=pk)
    
    user = get_or_auth_user(request)
    is_favorite = False
    if user:
        is_favorite = user.favorites.filter(product=product).exists()
    
    # Load reviews list
    reviews = product.reviews.select_related('user').order_by('-created_at')
    
    # Check if purchased
    can_review = False
    if user:
        from apps.orders.models import OrderItem
        can_review = OrderItem.objects.filter(
            order__user=user,
            order__status='yetkazildi',
            variant__product_id=product.id
        ).exists()
    
    # Load related products
    related_products = product.related_products.filter(is_active=True).prefetch_related('variants').annotate(min_price_val=Min('variants__price'))
    
    context = {
        'product': product,
        'is_favorite': is_favorite,
        'reviews': reviews,
        'can_review': can_review,
        'related_products': related_products,
    }
    return render(request, 'mahsulot.html', context)

@csrf_exempt
def toggle_favorite_view(request, product_id):
    """Toggle a product in user's favorites list."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

    user = get_or_auth_user(request)
    if not user:
        return JsonResponse({'status': 'error', 'message': 'Iltimos, avval tizimga kiring.'}, status=401)

    product = get_object_or_404(Product, pk=product_id)
    
    favorite, created = FavoriteProduct.objects.get_or_create(user=user, product=product)
    
    if not created:
        favorite.delete()
        is_favorite = False
        message = 'Mahsulot sevimlilardan olib tashlandi.'
    else:
        is_favorite = True
        message = 'Mahsulot sevimlilarga qo\'shildi.'

    return JsonResponse({
        'status': 'ok',
        'is_favorite': is_favorite,
        'message': message
    })

@csrf_exempt
def submit_review_view(request, product_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)
        
    user = get_or_auth_user(request)
    if not user:
        return JsonResponse({'status': 'error', 'message': 'Iltimos, avval tizimga kiring.'}, status=401)
        
    product = get_object_or_404(Product, pk=product_id)
    
    # Check if purchased and status is delivered
    from apps.orders.models import OrderItem
    has_purchased = OrderItem.objects.filter(
        order__user=user,
        order__status='yetkazildi',
        variant__product_id=product.id
    ).exists()
    
    if not has_purchased:
        return JsonResponse({'status': 'error', 'message': 'Faqat mahsulotni xarid qilgan mijozlar sharh qoldira oladilar.'}, status=403)
        
    try:
        data = json.loads(request.body)
        rating = int(data.get('rating', 0))
        comment = data.get('comment', '').strip()
        
        if rating < 1 or rating > 5:
            return JsonResponse({'status': 'error', 'message': 'Baho 1 va 5 oralig\'ida bo\'lishi kerak.'}, status=400)
            
        review, created = ProductReview.objects.update_or_create(
            product=product,
            user=user,
            defaults={
                'rating': rating,
                'comment': comment
            }
        )
        return JsonResponse({
            'status': 'ok',
            'message': 'Sharhingiz muvaffaqiyatli qabul qilindi. Rahmat!'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


from django.contrib import messages
from django.shortcuts import redirect

def product_by_barcode_view(request):
    barcode = request.GET.get('barcode', '').strip()
    if not barcode:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax') == '1':
            return JsonResponse({'status': 'error', 'message': 'Shtrix kod yuborilmadi'}, status=400)
        return redirect('catalog')

    try:
        variant = ProductVariant.objects.select_related('product').get(barcode=barcode)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax') == '1':
            return JsonResponse({
                'status': 'ok',
                'product_id': variant.product.id,
                'variant_id': variant.id,
                'product_name': variant.product.name,
                'label': variant.label,
                'price': variant.price,
                'stock_qty': variant.stock_qty,
                'image_url': variant.product.image.url if variant.product.image else ''
            })
        return redirect(f'/product/{variant.product.id}/')
    except ProductVariant.DoesNotExist:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax') == '1':
            return JsonResponse({'status': 'not_found', 'message': 'Mahsulot topilmadi'}, status=404)
        return redirect(f'/catalog/?barcode_not_found={barcode}')


def bundle_detail_view(request, pk):
    bundle = get_object_or_404(ProductBundle.objects.filter(is_active=True).prefetch_related('items__variant__product'), pk=pk)
    other_bundles = ProductBundle.objects.filter(is_active=True).exclude(id=bundle.id)[:4]
    
    context = {
        'bundle': bundle,
        'other_bundles': other_bundles,
    }
    return render(request, 'bundle_detail.html', context)
