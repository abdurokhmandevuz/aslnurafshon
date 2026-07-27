"""Django admin for orders app."""
import csv
from django.contrib import admin
from django.utils.html import format_html
from django.http import HttpResponse

from .models import Order, OrderItem, PromoCode, DeliveryTimeSlot, FeedbackRequest, CorporateInquiry, BankCard

@admin.register(BankCard)
class BankCardAdmin(admin.ModelAdmin):
    list_display = ('bank_name', 'card_number', 'card_holder', 'is_active', 'created_at')
    list_editable = ('is_active',)
    search_fields = ('bank_name', 'card_number', 'card_holder')


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percent', 'discount_amount', 'valid_until', 'usage_limit', 'times_used', 'is_active')
    search_fields = ('code',)
    list_filter = ('is_active', 'valid_until')


@admin.register(DeliveryTimeSlot)
class DeliveryTimeSlotAdmin(admin.ModelAdmin):
    list_display = ('date', 'label', 'start_time', 'end_time', 'max_orders', 'is_active')
    list_filter = ('is_active', 'date')
    search_fields = ('label',)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('bundle', 'product_name_snapshot', 'variant_weight_snapshot', 'quantity', 'price_at_order', 'line_total_display')
    can_delete = False

    def line_total_display(self, obj):
        return f"{obj.line_total:,} so'm"
    line_total_display.short_description = 'Jami'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user_display', 'courier', 'status_badge', 'payment_status_badge',
        'proof_preview', 'total_display', 'created_at',
    )
    list_filter = ('status', 'payment_status', 'courier', 'payment_method')
    search_fields = ('id', 'user__full_name', 'user__username', 'user__phone')
    readonly_fields = ('user', 'subtotal', 'promo_code', 'discount_amount', 'delivery_fee', 'total', 'proof_preview_detail', 'created_at', 'updated_at')
    inlines = [OrderItemInline]
    actions = ['confirm_payment', 'mark_as_preparing', 'mark_as_delivering', 'mark_as_delivered', 'export_to_csv']
    date_hierarchy = 'created_at'

    def _notify_async(self, order_id, status):
        import threading, asyncio
        from bot.notifications import notify_status_change
        def runner():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(notify_status_change(order_id, status))
            loop.close()
        threading.Thread(target=runner, daemon=True).start()

    def confirm_payment(self, request, queryset):
        for order in queryset:
            order.payment_status = 'paid'
            order.save(update_fields=['payment_status'])
        self.message_user(request, f"{queryset.count()} ta buyurtmaning to'lovi tasdiqlandi.")
    confirm_payment.short_description = "✅ To'lovni tasdiqlash ('To'langan' qilish)"

    def mark_as_preparing(self, request, queryset):
        for order in queryset:
            order.status = 'tayyorlanmoqda'
            order.save(update_fields=['status'])
            self._notify_async(order.id, 'tayyorlanmoqda')
        self.message_user(request, f"{queryset.count()} ta buyurtma 'Tayyorlanmoqda' holatiga o'tkazildi va mijozga bildirishnoma yuborildi.")
    mark_as_preparing.short_description = "👨‍🍳 Belgilanganlarni 'Tayyorlanmoqda' qilish"

    def mark_as_delivering(self, request, queryset):
        for order in queryset:
            order.status = 'yolda'
            order.save(update_fields=['status'])
            self._notify_async(order.id, 'yolda')
        self.message_user(request, f"{queryset.count()} ta buyurtma 'Yo'lda' holatiga o'tkazildi va mijozga bildirishnoma yuborildi.")
    mark_as_delivering.short_description = "🚚 Belgilanganlarni 'Yo'lda' qilish"

    def mark_as_delivered(self, request, queryset):
        for order in queryset:
            order.status = 'yetkazildi'
            order.payment_status = 'paid'
            order.save(update_fields=['status', 'payment_status'])
            self._notify_async(order.id, 'yetkazildi')
        self.message_user(request, f"{queryset.count()} ta buyurtma 'Yetkazildi' holatiga o'tkazildi va mijozga chek bilan bildirishnoma yuborildi.")
    mark_as_delivered.short_description = "✅ Belgilanganlarni 'Yetkazildi' qilish"

    def export_to_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="buyurtmalar.csv"'
        
        # Write UTF-8 BOM so Excel opens it with correct encoding
        response.write('\ufeff'.encode('utf8'))
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Mijoz', 'Telefon', 'Jami Summa (UZS)', 'Holat', 
            'To\'lov usuli', 'To\'lov holati', 'Manzil', 'Yaratilgan vaqt'
        ])
        
        for order in queryset.select_related('user', 'address'):
            writer.writerow([
                order.id,
                order.user.full_name if order.user else 'Noma\'lum',
                order.user.phone if order.user else '',
                order.total,
                order.get_status_display(),
                order.get_payment_method_display(),
                order.get_payment_status_display(),
                order.address.address_text if order.address else '',
                order.created_at.strftime('%d.%m.%Y %H:%M')
            ])
            
        return response
    export_to_csv.short_description = "CSV shaklida yuklab olish"


@admin.register(FeedbackRequest)
class FeedbackRequestAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'scheduled_time', 'is_sent', 'rating', 'comment', 'created_at')
    list_filter = ('is_sent', 'rating', 'created_at')
    search_fields = ('order__id', 'comment')
    readonly_fields = ('order', 'scheduled_time', 'is_sent', 'created_at')


@admin.register(CorporateInquiry)
class CorporateInquiryAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'contact_person', 'phone', 'estimated_quantity', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    list_editable = ('status',)
    search_fields = ('company_name', 'contact_person', 'phone', 'comment')
