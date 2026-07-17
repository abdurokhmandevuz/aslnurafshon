from django import template
from django.utils import timezone
from apps.orders.models import Order
from django.db.models import Sum

register = template.Library()

@register.inclusion_tag('admin/dashboard_stats.html')
def get_dashboard_stats():
    today = timezone.localtime().date()
    # Bugungi faol buyurtmalar (bekor qilinganlardan tashqari)
    today_orders = Order.objects.filter(
        created_at__date=today
    ).exclude(status='bekor_qilindi')
    
    orders_count = today_orders.count()
    total_revenue = today_orders.aggregate(total=Sum('total'))['total'] or 0
    
    return {
        'orders_count': orders_count,
        'total_revenue': total_revenue
    }
