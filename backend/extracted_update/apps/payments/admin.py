"""Django admin for payments app."""
from django.contrib import admin

from .models import ClickTransaction, PaymeTransaction


@admin.register(PaymeTransaction)
class PaymeTransactionAdmin(admin.ModelAdmin):
    list_display = ('payme_transaction_id', 'order', 'state', 'amount', 'create_time', 'perform_time')
    list_filter = ('state',)
    readonly_fields = ('payme_transaction_id', 'order', 'payme_time', 'amount', 'create_time', 'perform_time', 'cancel_time')
    search_fields = ('payme_transaction_id', 'order__id')


@admin.register(ClickTransaction)
class ClickTransactionAdmin(admin.ModelAdmin):
    list_display = ('click_trans_id', 'order', 'status', 'amount', 'created_at')
    list_filter = ('status',)
    readonly_fields = ('click_trans_id', 'order', 'amount', 'sign_time', 'created_at')
    search_fields = ('click_trans_id', 'merchant_trans_id', 'order__id')
