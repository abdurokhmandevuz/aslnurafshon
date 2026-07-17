import asyncio
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count
from apps.orders.models import Order, OrderItem
from bot.notifications import _get_bot
from django.conf import settings

class Command(BaseCommand):
    help = 'Sends a daily sales and orders report to the admin group via Telegram Bot.'

    def handle(self, *args, **options):
        # Last 24 hours
        time_threshold = timezone.now() - timedelta(days=1)
        orders = Order.objects.filter(created_at__gte=time_threshold)
        
        total_orders = orders.count()
        delivered_orders = orders.filter(status=Order.Status.DELIVERED).count()
        cancelled_orders = orders.filter(status=Order.Status.CANCELLED).count()
        new_orders = orders.filter(status=Order.Status.NEW).count()
        
        # Revenue
        total_revenue = orders.filter(
            status__in=[Order.Status.NEW, Order.Status.PREPARING, Order.Status.ON_THE_WAY, Order.Status.DELIVERED]
        ).aggregate(total=Sum('total'))['total'] or 0

        # Payments breakdown
        payments = orders.values('payment_method').annotate(
            count=Count('id'),
            sum=Sum('total')
        )
        payment_lines = []
        for p in payments:
            method_name = dict(Order.PaymentMethod.choices).get(p['payment_method'], p['payment_method'])
            payment_lines.append(f"  • {method_name}: <b>{p['count']} ta</b> ({p['sum']:,} UZS)")
        payments_text = "\n".join(payment_lines) if payment_lines else "  • Yo'q"

        # Top sold items
        top_items = OrderItem.objects.filter(
            order__created_at__gte=time_threshold,
            order__status__in=[Order.Status.NEW, Order.Status.PREPARING, Order.Status.ON_THE_WAY, Order.Status.DELIVERED]
        ).values('product_name_snapshot', 'variant_weight_snapshot').annotate(
            total_qty=Sum('quantity'),
            total_sum=Sum('order__total')  # line_total is in database but we can just use quantity
        ).order_by('-total_qty')[:5]

        items_lines = []
        for item in top_items:
            items_lines.append(f"  • {item['product_name_snapshot']} ({item['variant_weight_snapshot']}) × {item['total_qty']} ta")
        items_text = "\n".join(items_lines) if items_lines else "  • Sotilmagan"

        report_text = (
            f"📊 <b>KUNLIK SAVDO HISOBOTI</b>\n"
            f"📅 Sana: {timezone.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"📦 Jami buyurtmalar: <b>{total_orders} ta</b>\n"
            f"   • Yangi: {new_orders} ta\n"
            f"   • Yetkazildi: {delivered_orders} ta\n"
            f"   • Bekor qilindi: {cancelled_orders} ta\n\n"
            f"💰 Umumiy tushum: <b>{total_revenue:,} UZS</b>\n\n"
            f"💳 To'lov turlari bo'yicha:\n{payments_text}\n\n"
            f"🔝 Top 5 sotilgan mahsulotlar:\n{items_text}\n\n"
            f"☕ <i>Asl Nurafshon do'koni boti hisoboti.</i>"
        )

        async def send_report():
            bot = _get_bot()
            if bot:
                admin_group = settings.ADMIN_GROUP_ID
                if admin_group:
                    await bot.send_message(
                        chat_id=admin_group,
                        text=report_text,
                        parse_mode='HTML'
                    )
                await bot.session.close()

        loop = asyncio.get_event_loop()
        loop.run_until_complete(send_report())
        self.stdout.write(self.style.SUCCESS("Daily report sent successfully."))
