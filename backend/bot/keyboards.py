"""Keyboard builders for Nurafshon bot."""
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


def _url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Persistent reply keyboard at the bottom of chat."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🛍 Do'konni ochish (Web)"),
                KeyboardButton(text="☕ Choy tanlash (Bot)"),
            ],
            [
                KeyboardButton(text="📦 Buyurtmalarim"),
                KeyboardButton(text="🔄 Qayta buyurtma"),
            ],
            [
                KeyboardButton(text="📞 Aloqa va Manzil"),
            ],
        ],
        resize_keyboard=True,
        persistent=True,
    )


def main_menu_keyboard(frontend_url: str) -> InlineKeyboardMarkup:
    """Main start inline menu using InlineKeyboardBuilder with adjust(1, 1, 2, 2)."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🛍 Web App Do'kon",
        web_app=WebAppInfo(url=_url(frontend_url, "index.html")),
        style="primary",
    )
    builder.button(
        text="💬 Botda xarid qilish",
        callback_data="bot_catalog",
        style="success",
    )
    builder.button(
        text="📦 Buyurtmalarim",
        callback_data="my_orders",
    )
    builder.button(
        text="🔥 Aksiyalar",
        web_app=WebAppInfo(url=_url(frontend_url, "aksiyalar.html")),
        style="danger",
    )
    builder.button(
        text="🔄 Qayta buyurtma",
        callback_data="reorder_last",
    )
    builder.button(
        text="📞 Aloqa",
        callback_data="contact",
    )
    builder.adjust(1, 1, 2, 2)
    return builder.as_markup()


def request_phone_keyboard() -> ReplyKeyboardMarkup:
    """Request contact button."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon raqamimni yuborish", request_contact=True, style="success")],
            [KeyboardButton(text="❌ Bekor qilish", style="danger")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def request_location_keyboard() -> ReplyKeyboardMarkup:
    """Request location button."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Joylashuvimni yuborish (GPS)", request_location=True, style="success")],
            [KeyboardButton(text="✏️ Manzilni matn qilib yozish")],
            [KeyboardButton(text="❌ Bekor qilish", style="danger")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def shop_keyboard(frontend_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🛍 Web App Do'kon",
                web_app=WebAppInfo(url=_url(frontend_url, "index.html")),
                style="primary",
            ),
            InlineKeyboardButton(
                text="☕ Bot Katalogi",
                callback_data="bot_catalog",
                style="success",
            ),
        ]
    ])


def orders_keyboard(frontend_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="📦 Barcha buyurtmalar (Web)",
            web_app=WebAppInfo(url=_url(frontend_url, "buyurtmalar.html")),
        )
    ]])


def promo_keyboard(frontend_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🔥 Aksiyalarni ko'rish",
            web_app=WebAppInfo(url=_url(frontend_url, "aksiyalar.html")),
            style="danger",
        )
    ]])


def categories_inline_keyboard(categories) -> InlineKeyboardMarkup:
    buttons = []
    category_emojis = ["🍃", "☕", "🫖", "✨", "🎁", "⭐"]
    for idx, cat in enumerate(categories):
        emoji = category_emojis[idx % len(category_emojis)]
        buttons.append([InlineKeyboardButton(text=f"{emoji} {cat.name}", callback_data=f"cat:{cat.id}")])
    buttons.append([
        InlineKeyboardButton(text="🛒 Savat", callback_data="view_cart"),
        InlineKeyboardButton(text="🏠 Menu", callback_data="main_menu"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def products_inline_keyboard(products, category_id: int) -> InlineKeyboardMarkup:
    buttons = []
    for p in products:
        price = p.min_price or 0
        buttons.append([
            InlineKeyboardButton(
                text=f"{p.name} — {price:,} UZS",
                callback_data=f"prod:{p.id}",
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Kategoriyalar", callback_data="bot_catalog", style="danger"),
        InlineKeyboardButton(text="🛒 Savat", callback_data="view_cart"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def product_detail_inline_keyboard(product_id: int, variants) -> InlineKeyboardMarkup:
    buttons = []
    for v in variants:
        label = v.label or f"{v.weight_grams}g"
        buttons.append([
            InlineKeyboardButton(
                text=f"➕ {label} — {v.price:,} UZS",
                callback_data=f"addvar:{v.id}",
                style="success",
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="🛒 Savatni rasmiylashtirish", callback_data="view_cart", style="success"),
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Katalogga qaytish", callback_data="bot_catalog", style="danger"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def cart_inline_keyboard(has_items: bool) -> InlineKeyboardMarkup:
    if not has_items:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛍 Choy tanlash", callback_data="bot_catalog", style="success")],
            [InlineKeyboardButton(text="🏠 Bosh menu", callback_data="main_menu")],
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Buyurtma berish (Checkout)", callback_data="checkout_bot", style="success")],
        [InlineKeyboardButton(text="➕ Yana mahsulot qo'shish", callback_data="bot_catalog")],
        [InlineKeyboardButton(text="🗑 Savatni tozalash", callback_data="clear_cart", style="danger")],
    ])


def order_admin_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ To'lovni tasdiqlash", callback_data=f"order:confirm:{order_id}", style="success"),
            InlineKeyboardButton(text="🚚 Yo'lga chiqdi", callback_data=f"order:dispatch:{order_id}"),
        ],
        [
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"order:cancel:{order_id}", style="danger"),
        ],
    ])


def order_delivered_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Yetkazildi", callback_data=f"order:delivered:{order_id}", style="success")
    ]])


def web_app_button(frontend_url: str, text: str, path: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=text, web_app=WebAppInfo(url=_url(frontend_url, path)))
    ]])
