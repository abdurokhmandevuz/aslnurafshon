from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from apps.catalog.models import ProductVariant
from .models import Order, OrderItem
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


def get_or_auth_user(request):
    """
    Telegram Mini App'da session cookie ishlamasligi mumkin.
    Shuning uchun avval session'dan, keyin initData'dan user olamiz.
    """
    if request.user.is_authenticated:
        return request.user
    
    # initData dan auth qilishga urinib ko'ramiz
    init_data = request.GET.get('initData') or request.POST.get('initData') or ''
    if not init_data:
        # HTTP Header'dan ham tekshiramiz
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('TelegramInitData '):
            init_data = auth_header[len('TelegramInitData '):]
    
    if init_data:
        try:
            from apps.accounts.authentication import TelegramInitDataAuthentication
            auth = TelegramInitDataAuthentication()
            user_data = auth._validate_and_parse(init_data)
            user = auth._get_or_create_user(user_data)
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return user
        except Exception:
            pass
    
    return None


def cart_view(request):
    cart = request.session.get('cart', {})
    
    variant_ids = list(cart.keys())
    variants = ProductVariant.objects.filter(id__in=variant_ids).select_related('product')
    
    items = []
    total = 0
    for variant in variants:
        quantity = cart[str(variant.id)]
        line_total = variant.price * quantity
        total += line_total
        items.append({
            'variant': variant,
            'quantity': quantity,
            'line_total': line_total
        })
        
    context = {
        'items': items,
        'total': total,
        'cart_count': sum(cart.values())
    }
    return render(request, 'savat.html', context)


def checkout_view(request):
    cart = request.session.get('cart', {})
    if not cart:
        return redirect('catalog')
        
    variant_ids = list(cart.keys())
    variants = ProductVariant.objects.filter(id__in=variant_ids).select_related('product')
    
    total = 0
    items = []
    for variant in variants:
        quantity = cart[str(variant.id)]
        line_total = variant.price * quantity
        total += line_total
        items.append({
            'variant': variant,
            'quantity': quantity,
            'line_total': line_total
        })
        
    delivery_fee = 15000
    grand_total = total + delivery_fee
    
    user = get_or_auth_user(request)
    context = {
        'items': items,
        'subtotal': total,
        'delivery_fee': delivery_fee,
        'grand_total': grand_total,
        'user_phone': getattr(user, 'phone', '') if user else '',
    }
    return render(request, 'checkout.html', context)


def checkout_submit_view(request):
    if request.method != 'POST':
        return redirect('checkout')

    user = get_or_auth_user(request)
    if not user:
        return redirect('/')

    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, "Savatingiz bo'sh.")
        return redirect('cart')

    phone = request.POST.get('phone')
    address = request.POST.get('address')
    payment_method = request.POST.get('payment', 'naqd')
    delivery_time = request.POST.get('delivery_time', '')
    
    if phone and hasattr(user, 'phone'):
        user.phone = phone
        user.save(update_fields=['phone'])

    subtotal = 0
    items_data = []
    
    # Validation and prep
    for variant_id_str, quantity in cart.items():
        try:
            variant = ProductVariant.objects.select_related('product').get(id=int(variant_id_str))
            if variant.stock_qty < quantity:
                messages.error(request, f"Kechirasiz, {variant.product.name} ({variant.label}) dan omborda yetarli emas. Hozirda {variant.stock_qty} ta mavjud.")
                return redirect('cart')
                
            line_total = variant.price * quantity
            subtotal += line_total
            items_data.append({'variant': variant, 'quantity': quantity, 'price': variant.price})
        except ProductVariant.DoesNotExist:
            continue

    delivery_fee = 15000 if subtotal > 0 else 0
    grand_total = subtotal + delivery_fee

    order = Order.objects.create(
        user=user,
        status=Order.Status.NEW,
        payment_method=payment_method,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        total=grand_total,
        delivery_time_slot=delivery_time,
    )

    for item in items_data:
        variant = item['variant']
        qty = item['quantity']
        
        # Deduct stock
        variant.stock_qty -= qty
        variant.save(update_fields=['stock_qty'])
        
        OrderItem.objects.create(
            order=order,
            variant=variant,
            product_name_snapshot=variant.product.name,
            variant_weight_snapshot=variant.label,
            quantity=qty,
            price_at_order=item['price']
        )

    request.session['cart'] = {}
    request.session['last_order_id'] = order.id
    request.session.modified = True
    
    # Trigger Telegram bot notification via signal
    from apps.orders.signals import order_created
    order_created.send(sender=Order, order=order)
    
    return redirect('order_success')


def order_success_view(request):
    last_order_id = request.session.get('last_order_id')
    if not last_order_id:
        return redirect('catalog')
        
    order = get_object_or_404(Order.objects.prefetch_related('items__variant__product'), id=last_order_id)
    return render(request, 'tasdiqlandi.html', {'order': order})


def orders_view(request):
    user = get_or_auth_user(request)
    if not user:
        # Foydalanuvchi tizimga kirmagan — bosh sahifani ko'rsatamiz
        return render(request, 'buyurtmalar.html', {'orders': [], 'not_authenticated': True})
    
    orders = Order.objects.filter(user=user).order_by('-created_at')
    context = {
        'orders': orders
    }
    return render(request, 'buyurtmalar.html', context)


@csrf_exempt
def cart_update_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            variant_id = str(data.get('variant_id'))
            quantity = int(data.get('quantity', 0))
            
            cart = request.session.get('cart', {})
            if quantity > 0:
                cart[variant_id] = quantity
            else:
                if variant_id in cart:
                    del cart[variant_id]
                    
            request.session['cart'] = cart
            request.session.modified = True
            
            return JsonResponse({'status': 'ok', 'cart_count': sum(cart.values())})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'invalid method'}, status=405)
