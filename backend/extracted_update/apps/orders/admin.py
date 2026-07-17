"""Django admin for orders app."""
from django.contrib import admin
from django.utils.html import format_html

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_name_snapshot', 'variant_weight_snapshot', 'quantity', 'price_at_order', 'line_total_display')
    can_delete = False

    def line_total_display(self, obj):
        return f"{obj.line_total:,} so'm"
    line_total_display.short_description = 'Jami'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user_display', 'status_badge', 'payment_status_badge',
        'total_display', 'delivery_type', 'created_at',
    )
    list_filter = ('status', 'payment_status', 'delivery_type', 'payment_method')
    search_fields = ('id', 'user__full_name', 'user__username', 'user__phone_number')
    readonly_fields = ('user', 'subtotal', 'delivery_fee', 'total', 'created_at', 'updated_at')
    inlines = [OrderItemInline]
    actions = ['mark_as_preparing', 'mark_as_delivering', 'mark_as_delivered']
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
        colors = {'pending': '#f59e0b', 'paid': '#10b981', 'failed': '#ef4444'}
        color = colors.get(obj.payment_status, '#6b7280')
        return format_html(
            '<span style="background:{};color:white;padding:4px 10px;border-radius:12px;font-size:12px;font-weight:500;">{}</span>',
            color, obj.get_payment_status_display()
        )
    payment_status_badge.short_description = "To'lov"

    def total_display(self, obj):
        return f"{obj.total:,} so'm"
    total_display.short_description = 'Jami'

    @admin.action(description="Belgilanganlarni 'Tayyorlanmoqda' deb belgilash")
    def mark_as_preparing(self, request, queryset):
        for order in queryset:
            order.status = 'tayyorlanmoqda'
            order.save(update_fields=['status', 'updated_at'])

    @admin.action(description="Belgilanganlarni 'Yo'lda' deb belgilash")
    def mark_as_delivering(self, request, queryset):
        for order in queryset:
            order.status = 'yolda'
            order.save(update_fields=['status', 'updated_at'])

    @admin.action(description="Belgilanganlarni 'Yetkazildi' deb belgilash")
    def mark_as_delivered(self, request, queryset):
        for order in queryset:
            order.status = 'yetkazildi'
            order.save(update_fields=['status', 'updated_at'])
