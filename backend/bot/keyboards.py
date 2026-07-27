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
    """Main start inline menu."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🌐 Web App Do'kon",
                web_app=WebAppInfo(url=_url(frontend_url, "index.html")),
            ),
            InlineKeyboardButton(
                text="💬 Botda xarid qilish",
                callback_data="bot_catalog",
            ),
        ],
        [
            InlineKeyboardButton(
                text="📦 Buyurtmalarim",
                callback_data="my_orders",
            ),
            InlineKeyboardButton(
                text="🔥 Aksiyalar",
                web_app=WebAppInfo(url=_url(frontend_url, "aksiyalar.html")),
            ),
        ],
        [
            InlineKeyboardButton(text="🔄 Qayta buyurtma", callback_data="reorder_last"),
            InlineKeyboardButton(text="📞 Aloqa", callback_data="contact"),
        ],
    ])


def request_phone_keyboard() -> ReplyKeyboardMarkup:
    """Request contact button."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon raqamimni yuborish", request_contact=True)],
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def request_location_keyboard() -> ReplyKeyboardMarkup:
    """Request location button."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Joylashuvimni yuborish (GPS)", request_location=True)],
            [KeyboardButton(text="✏️ Manzilni matn qilib yozish")],
            [KeyboardButton(text="❌ Bekor qilish")],
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
            ),
            InlineKeyboardButton(
                text="☕ Bot Katalogi",
                callback_data="bot_catalog",
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
                callback_data=f"prod:{p.id}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Kategoriyalar", callback_data="bot_catalog"),
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
                callback_data=f"addvar:{v.id}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="🛒 Savatni rasmiylashtirish", callback_data="view_cart"),
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Katalogga qaytish", callback_data="bot_catalog"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def cart_inline_keyboard(has_items: bool) -> InlineKeyboardMarkup:
    if not has_items:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛍 Choy tanlash", callback_data="bot_catalog")],
            [InlineKeyboardButton(text="🏠 Bosh menu", callback_data="main_menu")],
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Buyurtma berish (Checkout)", callback_data="checkout_bot")],
        [InlineKeyboardButton(text="🗑 Savatni tozalash", callback_data="clear_cart")],
        [InlineKeyboardButton(text="➕ Yana mahsulot qo'shish", callback_data="bot_catalog")],
    ])


def order_admin_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ To'lovni tasdiqlash", callback_data=f"order:confirm:{order_id}"),
            InlineKeyboardButton(text="🚚 Yo'lga chiqdi", callback_data=f"order:dispatch:{order_id}"),
        ],
        [
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"order:cancel:{order_id}"),
        ],
    ])


def order_delivered_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Yetkazildi", callback_data=f"order:delivered:{order_id}")
    ]])


def web_app_button(frontend_url: str, text: str, path: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=text, web_app=WebAppInfo(url=_url(frontend_url, path)))
    ]])
