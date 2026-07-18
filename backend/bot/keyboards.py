"""Keyboard builders for Nurafshon bot."""
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)


def web_app_url(frontend_url: str, path: str = "/") -> str:
    return f"{frontend_url.rstrip('/')}/{path.lstrip('/')}"


# ─── Reply Keyboard (pastki tugmalar) ────────────────────────────────────────

def main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Foydalanuvchi pastida doim ko'rinadigan tugmalar."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🛍 Do'konni ochish"),
                KeyboardButton(text="🔥 Aksiyalar"),
            ],
            [
                KeyboardButton(text="📦 Buyurtmalarim"),
                KeyboardButton(text="📞 Aloqa"),
            ],
        ],
        resize_keyboard=True,
        persistent=True,
    )


# ─── Inline Keyboard (Web App tugmalari) ─────────────────────────────────────

def main_menu_keyboard(frontend_url: str) -> InlineKeyboardMarkup:
    """Start xabaridagi inline tugmalar."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛍 Do'konni ochish",
                    web_app=WebAppInfo(url=web_app_url(frontend_url, "catalog/")),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔥 Bugungi chegirmalar",
                    web_app=WebAppInfo(url=web_app_url(frontend_url, "promotions/")),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📦 Buyurtmalarim",
                    callback_data="my_orders",
                ),
                InlineKeyboardButton(
                    text="📞 Aloqa",
                    callback_data="contact",
                ),
            ],
        ]
    )


def shop_keyboard(frontend_url: str) -> InlineKeyboardMarkup:
    """Do'konni ochish tugmasi."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛍 Do'konni ochish",
                    web_app=WebAppInfo(url=web_app_url(frontend_url, "catalog/")),
                )
            ]
        ]
    )


def orders_keyboard(frontend_url: str) -> InlineKeyboardMarkup:
    """Buyurtmalar web app tugmasi."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📦 Barcha buyurtmalarni ko'rish",
                    web_app=WebAppInfo(url=web_app_url(frontend_url, "orders/")),
                )
            ]
        ]
    )


def promo_keyboard(frontend_url: str) -> InlineKeyboardMarkup:
    """Aksiyalar web app tugmasi."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔥 Barcha aksiyalarni ko'rish",
                    web_app=WebAppInfo(url=web_app_url(frontend_url, "promotions/")),
                )
            ]
        ]
    )


def web_app_button(frontend_url: str, text: str, path: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, web_app=WebAppInfo(url=web_app_url(frontend_url, path)))],
            [InlineKeyboardButton(text="🏠 Bosh menu", callback_data="main_menu")],
        ]
    )


# ─── Admin keyboard ───────────────────────────────────────────────────────────

def order_admin_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Tasdiqlash",
                    callback_data=f"order:confirm:{order_id}",
                ),
                InlineKeyboardButton(
                    text="🚚 Yo'lga chiqdi",
                    callback_data=f"order:dispatch:{order_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Bekor qilish",
                    callback_data=f"order:cancel:{order_id}",
                ),
            ],
        ]
    )


def order_delivered_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Yetkazildi",
                    callback_data=f"order:delivered:{order_id}",
                )
            ]
        ]
    )
