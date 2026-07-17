"""Django admin configuration for accounts app."""
from django.contrib import admin

from .models import Address, TelegramUser


class AddressInline(admin.TabularInline):
    model = Address
    extra = 0
    fields = ('title', 'address_text', 'latitude', 'longitude', 'is_default')


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'full_name', 'username', 'phone', 'created_at')
    search_fields = ('telegram_id', 'full_name', 'username', 'phone')
    readonly_fields = ('telegram_id', 'created_at')
    inlines = [AddressInline]


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'address_text', 'is_default', 'created_at')
    list_filter = ('is_default',)
    search_fields = ('user__full_name', 'address_text')
    raw_id_fields = ('user',)
