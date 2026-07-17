"""
Accounts application models.

TelegramUser  — authenticated bot/mini-app user
Address       — saved delivery addresses
"""
from django.db import models


class TelegramUser(models.Model):
    """Represents a Telegram user authenticated via WebApp initData."""

    telegram_id = models.BigIntegerField(unique=True, verbose_name='Telegram ID')
    full_name = models.CharField(max_length=255, verbose_name="To'liq ismi")
    username = models.CharField(max_length=64, blank=True, verbose_name='Username')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Telefon')
    language_code = models.CharField(max_length=8, blank=True, default='uz')
    last_login = models.DateTimeField(null=True, blank=True, verbose_name='Oxirgi faollik')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Foydalanuvchi'
        verbose_name_plural = 'Foydalanuvchilar'

    def __str__(self):
        return f'{self.full_name} (@{self.username or self.telegram_id})'

    # Django admin & DRF compatibility helpers
    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @property
    def is_active(self):
        return True

    @property
    def is_staff(self):
        return False

    def has_module_perms(self, app_label):
        return False

    def has_perm(self, perm, obj=None):
        return False

    def has_perms(self, perm_list, obj=None):
        return False

    def get_username(self):
        return self.username or str(self.telegram_id)


class Address(models.Model):
    """Saved delivery address for a TelegramUser."""

    user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name='addresses',
        verbose_name='Foydalanuvchi',
    )
    title = models.CharField(max_length=100, verbose_name='Sarlavha', help_text='Uy, Ish …')
    address_text = models.TextField(verbose_name='Manzil matni')
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name='Kenglik'
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name='Uzunlik'
    )
    is_default = models.BooleanField(default=False, verbose_name='Asosiy manzil')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Manzil'
        verbose_name_plural = 'Manzillar'
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f'{self.title} — {self.user}'

    def save(self, *args, **kwargs):
        # Ensure only one default address per user
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(
                is_default=False
            )
        super().save(*args, **kwargs)


class Courier(models.Model):
    """Courier profile added by Admin."""
    telegram_id = models.BigIntegerField(unique=True, verbose_name='Telegram ID')
    full_name = models.CharField(max_length=255, verbose_name="To'liq ismi")
    phone = models.CharField(max_length=20, verbose_name='Telefon')
    info = models.TextField(blank=True, null=True, verbose_name="Qo'shimcha ma'lumot")
    is_active = models.BooleanField(default=True, verbose_name='Faol')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Kuryer'
        verbose_name_plural = 'Kuryerlar'

    def __str__(self):
        return f'{self.full_name} ({self.phone})'
