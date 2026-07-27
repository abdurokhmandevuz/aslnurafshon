"""Keyboard builders — sodda versiya."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


def _url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


def main_menu_keyboard(frontend_url: str) -> InlineKeyboardMarkup:
    """Asosiy menyu — bir qatorda eng muhim tugmalar."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🛍 Do'konni ochish",
            web_app=WebAppInfo(url=_url(frontend_url, "index.html")),
        )],
        [
            InlineKeyboardButton(
                text="📦 Buyurtmalarim",
                web_app=WebAppInfo(url=_url(frontend_url, "buyurtmalar.html")),
            ),
            InlineKeyboardButton(
                text="🔥 Aksiyalar",
                web_app=WebAppInfo(url=_url(frontend_url, "aksiyalar.html")),
            ),
        ],
        [InlineKeyboardButton(text="📞 Aloqa", callback_data="contact")],
    ])


def shop_keyboard(frontend_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🛍 Do'konni ochish",
            web_app=WebAppInfo(url=_url(frontend_url, "index.html")),
        )
    ]])


def orders_keyboard(frontend_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="📦 Barcha buyurtmalar",
            web_app=WebAppInfo(url=_url(frontend_url, "buyurtmalar.html")),
        )
    ]])


def promo_keyboard(frontend_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🔥 Aksiyalarni ko'rish",
            web_app=WebAppInfo(url=_url(frontend_url, "aksiyalar.html")),
        )
    ]])


def order_admin_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash",   callback_data=f"order:confirm:{order_id}"),
            InlineKeyboardButton(text="🚚 Yo'lga chiqdi", callback_data=f"order:dispatch:{order_id}"),
        ],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"order:cancel:{order_id}")],
    ])


def order_delivered_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Yetkazildi", callback_data=f"order:delivered:{order_id}")
    ]])


# Eskilik uchun saqlab turamiz
def web_app_button(frontend_url: str, text: str, path: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=text, web_app=WebAppInfo(url=_url(frontend_url, path)))
    ]])
