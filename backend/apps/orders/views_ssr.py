from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from apps.catalog.models import ProductVariant
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Order, OrderItem, PromoCode, DeliveryTimeSlot

def get_or_auth_user(request):
    """
    Telegram Mini App'da session cookie ishlamasligi mumkin.
    Shuning uchun avval session'dan, keyin initData'dan user olamiz.
    """
    if request.user.is_authenticated:
        return request.user
    
    # initData dan auth qilishga urinib ko'ramiz
    init_data = request.GET.get('initData') or request.POST.get('initData') or request.headers.get('X-Init-Data') or ''
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
            login(request, user, backend='apps.accounts.backends.TelegramBackend')
            return user
        except Exception:
            pass
    
    return None


def cart_view(request):
    cart = request.session.get('cart', {})
    
    variant_ids = [vid for vid in cart.keys() if str(vid).isdigit()]
    variants = ProductVariant.objects.filter(id__in=variant_ids).select_related('product')
    
    bundle_keys = [k for k in cart.keys() if str(k).startswith('bundle_')]
    from apps.catalog.models import ProductBundle
    bundle_ids = [int(k.split('_')[1]) for k in bundle_keys]
    bundles = ProductBundle.objects.filter(id__in=bundle_ids).prefetch_related('items__variant__product')
    
    items = []
    total = 0
    for variant in variants:
        quantity = cart[str(variant.id)]
        line_total = variant.price * quantity
        total += line_total
        items.append({
            'type': 'variant',
            'id': variant.id,
            'variant': variant,
            'quantity': quantity,
            'line_total': line_total
        })
        
    for bundle in bundles:
        quantity = cart[f"bundle_{bundle.id}"]
        line_total = bundle.price * quantity
        total += line_total
        items.append({
            'type': 'bundle',
            'id': bundle.id,
            'bundle': bundle,
            'quantity': quantity,
            'line_total': line_total
        })
        
    applied_promo = request.session.get('applied_promo_code')
    discount = 0
    if applied_promo:
        try:
            promo = PromoCode.objects.get(code=applied_promo, is_active=True)
            if promo.is_valid(total):
                discount = promo.calculate_discount(total)
            else:
                del request.session['applied_promo_code']
                request.session.modified = True
                applied_promo = None
        except PromoCode.DoesNotExist:
            del request.session['applied_promo_code']
            request.session.modified = True
            applied_promo = None

    grand_total = max(0, total - discount)

    context = {
        'items': items,
        'total': total,
        'discount': discount,
        'applied_promo': applied_promo,
        'grand_total': grand_total,
        'cart_count': sum(cart.values())
    }
    return render(request, 'savat.html', context)


def checkout_view(request):
    cart = request.session.get('cart', {})
    if not cart:
        return redirect('catalog')
        
    variant_ids = [vid for vid in cart.keys() if str(vid).isdigit()]
    variants = ProductVariant.objects.filter(id__in=variant_ids).select_related('product')
    
    bundle_keys = [k for k in cart.keys() if str(k).startswith('bundle_')]
    from apps.catalog.models import ProductBundle
    bundle_ids = [int(k.split('_')[1]) for k in bundle_keys]
    bundles = ProductBundle.objects.filter(id__in=bundle_ids).prefetch_related('items__variant__product')
    
    total = 0
    items = []
    for variant in variants:
        quantity = cart[str(variant.id)]
        line_total = variant.price * quantity
        total += line_total
        items.append({
            'type': 'variant',
            'variant': variant,
            'quantity': quantity,
            'line_total': line_total
        })
        
    for bundle in bundles:
        quantity = cart[f"bundle_{bundle.id}"]
        line_total = bundle.price * quantity
        total += line_total
        items.append({
            'type': 'bundle',
            'bundle': bundle,
            'quantity': quantity,
            'line_total': line_total
        })
        
    applied_promo = request.session.get('applied_promo_code')
    discount = 0
    promo = None
    if applied_promo:
        try:
            promo = PromoCode.objects.get(code=applied_promo, is_active=True)
            if promo.is_valid(total):
                discount = promo.calculate_discount(total)
        except PromoCode.DoesNotExist:
            pass

    delivery_fee = 15000 if total > 0 else 0
    grand_total = max(0, total - discount + delivery_fee)
    
    MIN_ORDER_SUM = 50000
    is_under_min = total < MIN_ORDER_SUM

    user = get_or_auth_user(request)
    
    # Active delivery slots with capacity check (order_count < max_orders)
    from django.db.models import Count, Q, F
    from django.utils import timezone
    today = timezone.localdate()
    time_slots = DeliveryTimeSlot.objects.filter(
        is_active=True,
        date__gte=today
    ).annotate(
        order_count=Count('orders', filter=~Q(orders__status='bekor_qilindi'))
    ).filter(
        order_count__lt=F('max_orders')
    ).order_by('date', 'start_time')

    context = {
        'items': items,
        'subtotal': total,
        'discount': discount,
        'applied_promo': applied_promo,
        'delivery_fee': delivery_fee,
        'grand_total': grand_total,
        'user_phone': getattr(user, 'phone', '') if user else '',
        'min_order_sum': MIN_ORDER_SUM,
        'is_under_min': is_under_min,
        'time_slots': time_slots,
    }
    return render(request, 'checkout.html', context)


@csrf_exempt
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
    delivery_time_slot_id = request.POST.get('delivery_time_slot')
    
    if phone and hasattr(user, 'phone'):
        user.phone = phone
        user.save(update_fields=['phone'])

    subtotal = 0
    items_data = []
    
    # Validation and prep
    from apps.catalog.models import ProductBundle
    for key_str, quantity in cart.items():
        if key_str.startswith('bundle_'):
            try:
                bundle_id = int(key_str.split('_')[1])
                bundle = ProductBundle.objects.prefetch_related('items__variant__product').get(id=bundle_id)
                for b_item in bundle.items.all():
                    v = b_item.variant
                    required_qty = b_item.quantity * quantity
                    if v.stock_qty < required_qty:
                        messages.error(request, f"Kechirasiz, {v.product.name} ({v.label}) dan omborda yetarli emas. Hozirda {v.stock_qty} ta mavjud.")
                        return redirect('cart')
                        
                    discounted_price = int(v.price * (100 - bundle.discount_percent) / 100)
                    line_total = discounted_price * required_qty
                    subtotal += line_total
                    items_data.append({
                        'variant': v,
                        'quantity': required_qty,
                        'price': discounted_price,
                        'bundle': bundle
                    })
            except ProductBundle.DoesNotExist:
                continue
        elif key_str.isdigit():
            try:
                variant = ProductVariant.objects.select_related('product').get(id=int(key_str))
                if variant.stock_qty < quantity:
                    messages.error(request, f"Kechirasiz, {variant.product.name} ({variant.label}) dan omborda yetarli emas. Hozirda {variant.stock_qty} ta mavjud.")
                    return redirect('cart')
                    
                line_total = variant.price * quantity
                subtotal += line_total
                items_data.append({
                    'variant': variant,
                    'quantity': quantity,
                    'price': variant.price,
                    'bundle': None
                })
            except ProductVariant.DoesNotExist:
                continue

    MIN_ORDER_SUM = 50000
    if subtotal < MIN_ORDER_SUM:
        messages.error(request, f"Minimal buyurtma summasi {MIN_ORDER_SUM:,} so'm bo'lishi kerak. Hozirgi summa: {subtotal:,} so'm.")
        return redirect('checkout')

    applied_promo = request.session.get('applied_promo_code')
    promo = None
    discount = 0
    if applied_promo:
        try:
            promo = PromoCode.objects.get(code=applied_promo, is_active=True)
            if promo.is_valid(subtotal):
                discount = promo.calculate_discount(subtotal)
        except PromoCode.DoesNotExist:
            pass

    delivery_fee = 15000 if subtotal > 0 else 0
    grand_total = max(0, subtotal - discount + delivery_fee)

    # Resolve selected DeliveryTimeSlot
    from django.db.models import Count, Q
    slot = None
    if delivery_time_slot_id:
        try:
            slot = DeliveryTimeSlot.objects.annotate(
                order_count=Count('orders', filter=~Q(orders__status='bekor_qilindi'))
            ).get(id=int(delivery_time_slot_id), is_active=True)
            
            if slot.order_count >= slot.max_orders:
                messages.error(request, "Tanlangan vaqt oralig'i to'lib qoldi. Iltimos, boshqa vaqtni tanlang.")
                return redirect('checkout')
        except (DeliveryTimeSlot.DoesNotExist, ValueError):
            pass

    address_obj = None
    if address:
        from apps.accounts.models import Address
        address_obj, _ = Address.objects.get_or_create(
            user=user,
            address_text=address,
            defaults={'title': "Xaritadan tanlangan"}
        )

    order = Order.objects.create(
        user=user,
        status=Order.Status.NEW,
        payment_method=payment_method,
        subtotal=subtotal,
        promo_code=promo,
        discount_amount=discount,
        delivery_fee=delivery_fee,
        total=grand_total,
        delivery_time_slot=slot,
        address=address_obj,
    )

    if promo:
        promo.times_used += 1
        promo.save(update_fields=['times_used'])

    for item in items_data:
        variant = item['variant']
        qty = item['quantity']
        
        # Deduct stock
        variant.stock_qty -= qty
        variant.save(update_fields=['stock_qty'])
        
        OrderItem.objects.create(
            order=order,
            variant=variant,
            bundle=item['bundle'],
            product_name_snapshot=variant.product.name,
            variant_weight_snapshot=variant.label,
            quantity=qty,
            price_at_order=item['price']
        )

    request.session['cart'] = {}
    if 'applied_promo_code' in request.session:
        del request.session['applied_promo_code']
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
    order = get_object_or_404(Order, id=last_order_id)
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
            variant_id = data.get('variant_id')
            bundle_id = data.get('bundle_id')
            quantity = int(data.get('quantity', 0))
            
            cart = request.session.get('cart', {})
            key = None
            if variant_id is not None:
                key = str(variant_id)
            elif bundle_id is not None:
                key = f"bundle_{bundle_id}"

            if key:
                if quantity > 0:
                    cart[key] = quantity
                else:
                    if key in cart:
                        del cart[key]
                    
            request.session['cart'] = cart
            request.session.modified = True
            
            return JsonResponse({'status': 'ok', 'cart_count': sum(cart.values())})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'invalid method'}, status=405)


@csrf_exempt
def apply_promo_view(request):
    """
    Apply promo-code. Validate it and store it in user's session.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)
    
    try:
        data = json.loads(request.body)
        code_str = data.get('code', '').strip().upper()
        
        if not code_str:
            if 'applied_promo_code' in request.session:
                del request.session['applied_promo_code']
                request.session.modified = True
            return JsonResponse({
                'status': 'ok',
                'code': '',
                'discount': 0,
                'message': 'Promo-kod olib tashlandi.'
            })
            
        # Calculate subtotal of cart items
        cart = request.session.get('cart', {})
        subtotal = 0
        variant_ids = [vid for vid in cart.keys() if str(vid).isdigit()]
        variants = ProductVariant.objects.filter(id__in=variant_ids)
        for variant in variants:
            quantity = cart[str(variant.id)]
            subtotal += variant.price * quantity
            
        try:
            promo = PromoCode.objects.get(code=code_str, is_active=True)
        except PromoCode.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Promo-kod noto\'g\'ri yoki faol emas.'}, status=400)
            
        if not promo.is_valid(subtotal):
            return JsonResponse({'status': 'error', 'message': 'Promo-kod muddati o\'tgan, ishlatilish limiti tugagan yoki buyurtma summasi kam.'}, status=400)
            
        discount = promo.calculate_discount(subtotal)
        
        request.session['applied_promo_code'] = promo.code
        request.session.modified = True
        
        return JsonResponse({
            'status': 'ok',
            'code': promo.code,
            'discount': discount,
            'message': f'Promo-kod muvaffaqiyatli qo\'llandi! Chegirma: {discount:,} so\'m.'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


def repeat_order_view(request, order_id):
    """
    Repeat a past order by copying its items into the active cart session.
    """
    user = get_or_auth_user(request)
    if not user:
        return redirect('/')
        
    order = get_object_or_404(Order, id=order_id, user=user)
    
    cart = request.session.get('cart', {})
    added_any = False
    
    for item in order.items.all():
        if item.variant and item.variant.is_available and item.variant.stock_qty > 0:
            cart[str(item.variant.id)] = min(item.quantity, item.variant.stock_qty)
            added_any = True
            
    if added_any:
        request.session['cart'] = cart
        request.session.modified = True
        messages.success(request, "Buyurtma elementlari savatga qo'shildi.")
    else:
        messages.error(request, "Kechirasiz, ushbu buyurtmadagi barcha mahsulotlar tugagan.")
        
    return redirect('cart')


from django.views.i18n import set_language

@csrf_exempt
def set_language_exempt(request):
    return set_language(request)


def corporate_inquiry_view(request):
    if request.method == 'POST':
        company_name = request.POST.get('company_name', '').strip()
        contact_person = request.POST.get('contact_person', '').strip()
        phone = request.POST.get('phone', '').strip()
        estimated_quantity = request.POST.get('estimated_quantity', '1').strip()
        comment = request.POST.get('comment', '').strip()

        if not (company_name and contact_person and phone):
            messages.error(request, "Iltimos, barcha majburiy maydonlarni to'ldiring.")
            return render(request, 'corporate.html', {
                'company_name': company_name,
                'contact_person': contact_person,
                'phone': phone,
                'estimated_quantity': estimated_quantity,
                'comment': comment
            })

        try:
            qty = int(estimated_quantity)
        except ValueError:
            qty = 1

        inquiry = CorporateInquiry.objects.create(
            company_name=company_name,
            contact_person=contact_person,
            phone=phone,
            estimated_quantity=qty,
            comment=comment
        )

        messages.success(request, "Sizning korporativ so'rovingiz muvaffaqiyatli qabul qilindi. Tez orada siz bilan bog'lanamiz!")
        
        # Fire bot notification in background thread
        t = threading.Thread(target=_fire_corporate_notification, args=(inquiry.id,), daemon=True)
        t.start()
        
        return redirect('catalog')

    return render(request, 'corporate.html')


def _fire_corporate_notification(inquiry_id):
    try:
        import asyncio
        from bot.notifications import notify_corporate_inquiry
        asyncio.run(notify_corporate_inquiry(inquiry_id))
    except Exception:
        pass
