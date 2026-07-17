"""Django admin configuration for accounts app."""
from django.contrib import admin

from .models import Address, TelegramUser, Courier


@admin.register(Courier)
class CourierAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'full_name', 'phone', 'is_active', 'created_at')
    search_fields = ('telegram_id', 'full_name', 'phone')
    list_filter = ('is_active',)
    readonly_fields = ('created_at',)


class AddressInline(admin.TabularInline):
    model = Address
    extra = 0
    fields = ('title', 'address_text', 'latitude', 'longitude', 'is_default')


from django.db import models
from django.db.models import Sum, Count, Max
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.shortcuts import render
from django.http import HttpResponseRedirect


class SpendLevelFilter(admin.SimpleListFilter):
    title = 'Xarid darajasi'
    parameter_name = 'spend_level'

    def lookups(self, request, model_admin):
        return (
            ('high', 'Yuqori (> 500k so\'m)'),
            ('mid', 'O\'rta (100k - 500k so\'m)'),
            ('low', 'Past (< 100k so\'m)'),
            ('none', 'Xarid qilmagan'),
        )

    def queryset(self, request, queryset):
        val = self.value()
        if val == 'high':
            return queryset.filter(annotated_total_spent__gt=500000)
        elif val == 'mid':
            return queryset.filter(annotated_total_spent__gte=100000, annotated_total_spent__lte=500000)
        elif val == 'low':
            return queryset.filter(annotated_total_spent__gt=0, annotated_total_spent__lt=100000)
        elif val == 'none':
            return queryset.filter(annotated_total_spent=0)
        return queryset


class ActivityFilter(admin.SimpleListFilter):
    title = 'Faollik darajasi'
    parameter_name = 'activity_level'

    def lookups(self, request, model_admin):
        return (
            ('active', 'Faol (< 30 kun oldin)'),
            ('inactive', 'Nofaol (> 30 kun oldin)'),
            ('never', 'Hech qachon buyurtma bermagan'),
        )

    def queryset(self, request, queryset):
        val = self.value()
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(days=30)
        
        if val == 'active':
            return queryset.filter(annotated_last_order_date__gte=cutoff)
        elif val == 'inactive':
            return queryset.filter(annotated_last_order_date__lt=cutoff)
        elif val == 'never':
            return queryset.filter(annotated_last_order_date__isnull=True)
        return queryset


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'full_name', 'username', 'phone', 'total_orders_count', 'total_spent_display', 'days_since_last_order', 'created_at')
    list_filter = (SpendLevelFilter, ActivityFilter, 'created_at')
    search_fields = ('telegram_id', 'full_name', 'username', 'phone')
    readonly_fields = ('telegram_id', 'created_at')
    inlines = [AddressInline]
    actions = ['broadcast_message']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(
            annotated_orders_count=Count('orders', distinct=True),
            annotated_total_spent=Coalesce(Sum('orders__total', filter=models.Q(orders__status='yetkazildi')), 0),
            annotated_last_order_date=Max('orders__created_at')
        )
        return qs

    def total_orders_count(self, obj):
        return obj.annotated_orders_count
    total_orders_count.short_description = "Buyurtmalar soni"
    total_orders_count.admin_order_field = "annotated_orders_count"

    def total_spent_display(self, obj):
        return f"{obj.annotated_total_spent:,} so'm"
    total_spent_display.short_description = "Umumiy xarid"
    total_spent_display.admin_order_field = "annotated_total_spent"

    def days_since_last_order(self, obj):
        last_date = obj.annotated_last_order_date
        if last_date:
            delta = timezone.now() - last_date
            return f"{delta.days} kun"
        return "—"
    days_since_last_order.short_description = "Oxirgi buyurtmadan beri"
    days_since_last_order.admin_order_field = "annotated_last_order_date"

    def broadcast_message(self, request, queryset):
        if 'apply' in request.POST:
            message_text = request.POST.get('message_text', '').strip()
            if not message_text:
                self.message_user(request, "Xabar matni bo'sh bo'lishi mumkin emas.", level='error')
                return
            
            selected_ids = list(queryset.values_list('telegram_id', flat=True))
            import threading
            t = threading.Thread(target=self._send_broadcast, args=(selected_ids, message_text), daemon=True)
            t.start()
            
            self.message_user(request, f"{len(selected_ids)} ta foydalanuvchiga xabar yuborish boshlandi (fon rejimida).")
            return HttpResponseRedirect(request.get_full_path())
            
        return render(request, 'admin/broadcast_message.html', context={
            'users': queryset,
            'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
        })
    broadcast_message.short_description = "Tanlangan foydalanuvchilarga xabar yuborish"

    def _send_broadcast(self, telegram_ids, message_text):
        import asyncio
        from bot.notifications import _get_bot
        bot = _get_bot()
        if not bot:
            return
        
        async def send_all():
            for tid in telegram_ids:
                try:
                    await bot.send_message(chat_id=tid, text=message_text, parse_mode='HTML')
                    await asyncio.sleep(0.05)
                except Exception:
                    pass
            # Close bot session safely
            await bot.session.close()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_all())
        loop.close()


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'address_text', 'is_default', 'created_at')
    list_filter = ('is_default',)
    search_fields = ('user__full_name', 'address_text')
    raw_id_fields = ('user',)
