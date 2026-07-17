from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.orders.models import Order
from apps.accounts.models import Courier
from django.http import HttpResponseForbidden

def courier_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/')
        is_courier = Courier.objects.filter(telegram_id=request.user.telegram_id, is_active=True).exists()
        if not is_courier:
            return HttpResponseForbidden("Siz kuryer emassiz.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@courier_required
def courier_dashboard_view(request):
    courier = get_object_or_404(Courier, telegram_id=request.user.telegram_id, is_active=True)
    
    # Yangi buyurtmalar (hali hech kim olmagan)
    new_orders = Order.objects.filter(
        status__in=[Order.Status.NEW, Order.Status.PREPARING],
        courier__isnull=True
    ).order_by('-created_at')
    
    # Ushbu kuryerga tegishli faol buyurtmalar (yo'ldagi yoki olingan)
    my_active_orders = Order.objects.filter(
        status__in=[Order.Status.NEW, Order.Status.PREPARING, Order.Status.ON_THE_WAY],
        courier=courier
    ).order_by('-created_at')
    
    # Oxirgi yetkazilgan buyurtmalar
    completed_orders = Order.objects.filter(
        status=Order.Status.DELIVERED,
        courier=courier
    ).order_by('-updated_at')[:10]
    
    return render(request, 'courier/dashboard.html', {
        'courier': courier,
        'new_orders': new_orders,
        'my_active_orders': my_active_orders,
        'completed_orders': completed_orders,
    })

@courier_required
def courier_order_action_view(request, order_id, action):
    courier = get_object_or_404(Courier, telegram_id=request.user.telegram_id, is_active=True)
    order = get_object_or_404(Order, id=order_id)
    
    if action == 'take':
        if order.courier and order.courier != courier:
            messages.error(request, "Ushbu buyurtmani boshqa kuryer olgan.")
        else:
            order.courier = courier
            order.save(update_fields=['courier', 'updated_at'])
            messages.success(request, f"Buyurtma #{order.id} qabul qilindi.")
            
    elif action == 'start':
        if order.courier != courier:
            messages.error(request, "Bu buyurtma sizga tegishli emas.")
        else:
            order.status = Order.Status.ON_THE_WAY
            order.save(update_fields=['status', 'updated_at'])
            messages.success(request, f"Buyurtma #{order.id} yo'lga chiqdi deb belgilandi.")
            
    elif action == 'deliver':
        if order.courier != courier:
            messages.error(request, "Bu buyurtma sizga tegishli emas.")
        else:
            order.status = Order.Status.DELIVERED
            order.save(update_fields=['status', 'updated_at'])
            messages.success(request, f"Buyurtma #{order.id} yetkazib berildi!")
            
    return redirect('courier_dashboard')
