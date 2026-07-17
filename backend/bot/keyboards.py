"""
Keyboard builders for Nurafshon bot.
"""
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)


def main_menu_keyboard(frontend_url: str) -> InlineKeyboardMarkup:
    """Main inline keyboard with "Open shop" WebApp button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛑 Do'konni ochish",
                    web_app=WebAppInfo(url=f"{frontend_url}start/"),
                )
            ],
            [
                InlineKeyboardButton(
                    text='📦 Buyurtmalarim',
                    callback_data='my_orders'
                )
            ],
        ]
    )


def order_admin_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """
    Admin group inline keyboard for a new order:
    - Tasdiqlash (set status → tayyorlanmoqda)
    - Yetkazishga chiqarish (set status → yolda)
    - Bekor qilish (set status → bekor_qilindi)
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text='✅ Tasdiqlash',
                    callback_data=f'order:confirm:{order_id}',
                ),
                InlineKeyboardButton(
                    text='🚴 Yetkazishga chiqarish',
                    callback_data=f'order:dispatch:{order_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    text='❌ Bekor qilish',
                    callback_data=f'order:cancel:{order_id}',
                ),
            ],
        ]
    )


def order_delivered_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Mark an order as delivered."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text='✔️ Yetkazildi',
                    callback_data=f'order:delivered:{order_id}',
                )
            ]
        ]
    )
