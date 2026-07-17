"""Django admin for orders app."""
import csv
from django.contrib import admin
from django.utils.html import format_html
from django.http import HttpResponse

from .models import Order, OrderItem, PromoCode, DeliveryTimeSlot, FeedbackRequest, CorporateInquiry

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
        'total_display', 'created_at',
    )
    list_filter = ('status', 'payment_status', 'courier', 'payment_method')
    search_fields = ('id', 'user__full_name', 'user__username', 'user__phone')
    readonly_fields = ('user', 'subtotal', 'promo_code', 'discount_amount', 'delivery_fee', 'total', 'created_at', 'updated_at')
    inlines = [OrderItemInline]
    actions = ['mark_as_preparing', 'mark_as_delivering', 'mark_as_delivered', 'export_to_csv']
    date_hierarchy = 'created_at'
    list_per_page = 30

    def user_display(self, obj):
        if obj.user:
            return f"{obj.user.full_name} ({getattr(obj.user, 'phone_number', '')})"
        return "Noma'lum"
    user_display.short_description = 'Mijoz'

    def status_badge(self, obj):
        colors = {
            'yangi': '#C7E0F4',
            'tayyorlanmoqda': '#FFDF99',
            'yolda': '#EADDFF',
            'yetkazildi': '#C4EED0',
            'bekor_qilindi': '#FFDAD6',
        }
        color = colors.get(obj.status, '#eeeeee')
        return format_html(
            '<span style="background:{};color:black;padding:4px 10px;border-radius:12px;font-size:12px;font-weight:500;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Holat'

    def payment_status_badge(self, obj):
        colors = {
            'pending': '#FFE082',
            'paid': '#C8E6C9',
            'failed': '#FFCDD2',
        }
        color = colors.get(obj.payment_status, '#eeeeee')
        return format_html(
            '<span style="background:{};color:black;padding:4px 10px;border-radius:12px;font-size:12px;font-weight:500;">{}</span>',
            color, obj.get_payment_status_display()
        )
    payment_status_badge.short_description = "To'lov"

    def total_display(self, obj):
        return f"{obj.total:,} so'm"
    total_display.short_description = 'Jami'

    def mark_as_preparing(self, request, queryset):
        queryset.update(status='tayyorlanmoqda')
    mark_as_preparing.short_description = "Belgilanganlarni 'Tayyorlanmoqda' qilish"

    def mark_as_delivering(self, request, queryset):
        queryset.update(status='yolda')
    mark_as_delivering.short_description = "Belgilanganlarni 'Yo'lda' qilish"

    def mark_as_delivered(self, request, queryset):
        queryset.update(status='yetkazildi')
    mark_as_delivered.short_description = "Belgilanganlarni 'Yetkazildi' qilish"

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
