"""Keyboard builders for Nurafshon bot."""
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
)


def _url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Persistent reply keyboard at the bottom of chat."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🛍 Do'konni ochish (Web)", style="primary"),
                KeyboardButton(text="☕ Choy tanlash (Bot)", style="success"),
            ],
            [
                KeyboardButton(text="📦 Buyurtmalarim", style="primary"),
                KeyboardButton(text="🔄 Qayta buyurtma", style="success"),
            ],
            [
                KeyboardButton(text="📞 Aloqa va Manzil", style="primary"),
            ],
        ],
        resize_keyboard=True,
        persistent=True,
    )


def main_menu_keyboard(frontend_url: str) -> InlineKeyboardMarkup:
    """Main start inline menu."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🌐 Web App Do'kon",
                web_app=WebAppInfo(url=_url(frontend_url, "index.html")),
                style="primary",
            ),
            InlineKeyboardButton(
                text="💬 Botda xarid qilish",
                callback_data="bot_catalog",
                style="success",
            ),
        ],
        [
            InlineKeyboardButton(
                text="📦 Buyurtmalarim",
                callback_data="my_orders",
                style="primary",
            ),
            InlineKeyboardButton(
                text="🔥 Aksiyalar",
                web_app=WebAppInfo(url=_url(frontend_url, "aksiyalar.html")),
                style="danger",
            ),
        ],
        [
            InlineKeyboardButton(text="🔄 Qayta buyurtma", callback_data="reorder_last", style="success"),
            InlineKeyboardButton(text="📞 Aloqa", callback_data="contact", style="primary"),
        ],
    ])


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
            [KeyboardButton(text="✏️ Manzilni matn qilib yozish", style="primary")],
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
            style="primary",
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
        buttons.append([InlineKeyboardButton(text=f"{emoji} {cat.name}", callback_data=f"cat:{cat.id}", style="primary")])
    buttons.append([
        InlineKeyboardButton(text="🛒 Savat", callback_data="view_cart", style="success"),
        InlineKeyboardButton(text="🏠 Menu", callback_data="main_menu", style="primary"),
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
                style="primary",
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Kategoriyalar", callback_data="bot_catalog", style="primary"),
        InlineKeyboardButton(text="🛒 Savat", callback_data="view_cart", style="success"),
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
        InlineKeyboardButton(text="🛒 Savatni rasmiylashtirish", callback_data="view_cart", style="primary"),
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Katalogga qaytish", callback_data="bot_catalog", style="primary"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def cart_inline_keyboard(has_items: bool) -> InlineKeyboardMarkup:
    if not has_items:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛍 Choy tanlash", callback_data="bot_catalog", style="success")],
            [InlineKeyboardButton(text="🏠 Bosh menu", callback_data="main_menu", style="primary")],
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Buyurtma berish (Checkout)", callback_data="checkout_bot", style="success")],
        [InlineKeyboardButton(text="➕ Yana mahsulot qo'shish", callback_data="bot_catalog", style="primary")],
        [InlineKeyboardButton(text="🗑 Savatni tozalash", callback_data="clear_cart", style="danger")],
    ])


def order_admin_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ To'lovni tasdiqlash", callback_data=f"order:confirm:{order_id}", style="success"),
            InlineKeyboardButton(text="🚚 Yo'lga chiqdi", callback_data=f"order:dispatch:{order_id}", style="primary"),
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
        InlineKeyboardButton(text=text, web_app=WebAppInfo(url=_url(frontend_url, path)), style="primary")
    ]])
