"""
Telegram bot handlers — sodda va tez versiya.

Faqat zarur funksiyalar:
  - /start → bir xabar, Web App tugmasi
  - /orders (📦) → DB dan oxirgi buyurtmalar
  - /contact (📞) → aloqa matni
  - order: callbacks → admin status o'zgartirish
  - notify: yangi buyurtma + status xabarlari
"""
import logging
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

import django
django.setup()

from django.conf import settings
from aiogram import F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery

from bot.keyboards import (
    main_menu_keyboard,
    orders_keyboard,
    shop_keyboard,
    order_admin_keyboard,
    order_delivered_keyboard,
)

logger = logging.getLogger(__name__)
router = Router()

# ─── Status mapping ───────────────────────────────────────────
STATUS_EMOJI  = {'yangi':'🆕','tayyorlanmoqda':'👨‍🍳','yolda':'🚚','yetkazildi':'✅','bekor_qilindi':'❌'}
STATUS_LABEL  = {'yangi':'Yangi','tayyorlanmoqda':'Tayyorlanmoqda','yolda':"Yo'lda",'yetkazildi':'Yetkazildi','bekor_qilindi':'Bekor qilindi'}
STATUS_MAP    = {'confirm':'tayyorlanmoqda','dispatch':'yolda','delivered':'yetkazildi','cancel':'bekor_qilindi'}

CONTACT_TEXT = (
    "📞 <b>Aloqa</b>\n\n"
    "📱 +998 90 000 00 00\n"
    "📍 Nurafshon va yaqin hududlar\n"
    "⏰ 09:00 — 22:00\n\n"
    "Savol bo'lsa shu chatga yozing."
)


# ─── /start ───────────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user

    # Foydalanuvchini DB ga saqlash (background, bloklamasdan)
    try:
        from asgiref.sync import sync_to_async
        from apps.accounts.models import TelegramUser
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        await sync_to_async(TelegramUser.objects.update_or_create)(
            telegram_id=user.id,
            defaults={'full_name': full_name or str(user.id), 'username': user.username or ''},
        )
    except Exception as e:
        logger.warning("save_user error: %s", e)

    await message.answer(
        f"Assalomu alaykum, <b>{user.first_name}</b>! 👋\n\n"
        "☕ <b>Asl Nurafshon</b> — sifatli choy va kofe do'koni\n\n"
        "🛍 Do'konni ochish uchun quyidagi tugmani bosing 👇",
        parse_mode='HTML',
        reply_markup=main_menu_keyboard(settings.FRONTEND_URL),
    )


# ─── Do'konni ochish ──────────────────────────────────────────
@router.message(Command("shop"))
@router.message(F.text == "🛍 Do'konni ochish")
async def cmd_shop(message: Message):
    await message.answer(
        "🛍 <b>Do'konni ochish</b> uchun bosing 👇",
        parse_mode='HTML',
        reply_markup=shop_keyboard(settings.FRONTEND_URL),
    )


# ─── Aksiyalar ────────────────────────────────────────────────
@router.message(Command("promo"))
@router.message(F.text == "🔥 Aksiyalar")
async def cmd_promo(message: Message):
    from bot.keyboards import promo_keyboard
    await message.answer(
        "🔥 <b>Bugungi aksiyalar</b> 👇",
        parse_mode='HTML',
        reply_markup=promo_keyboard(settings.FRONTEND_URL),
    )


# ─── Buyurtmalarim ────────────────────────────────────────────
@router.message(Command("orders"))
@router.message(F.text == "📦 Buyurtmalarim")
async def cmd_orders(message: Message):
    try:
        from asgiref.sync import sync_to_async
        from apps.orders.models import Order

        orders = await sync_to_async(lambda: list(
            Order.objects.filter(user__telegram_id=message.from_user.id)
            .only('id', 'status', 'total_amount', 'created_at')
            .order_by('-created_at')[:5]
        ))()

        if not orders:
            await message.answer(
                "📦 Hali buyurtma yo'q.\n\nDo'kondan mahsulot tanlang! 🛍",
                reply_markup=shop_keyboard(settings.FRONTEND_URL),
            )
            return

        lines = ["<b>📦 Oxirgi buyurtmalar:</b>\n"]
        for o in orders:
            e = STATUS_EMOJI.get(o.status, '•')
            l = STATUS_LABEL.get(o.status, o.status)
            lines.append(f"{e} <b>#{o.id}</b> — {l}\n💰 {int(o.total_amount):,} UZS | {o.created_at.strftime('%d.%m.%y')}\n")

        await message.answer(
            "\n".join(lines),
            parse_mode='HTML',
            reply_markup=orders_keyboard(settings.FRONTEND_URL),
        )
    except Exception as e:
        logger.error("orders error: %s", e)
        await message.answer("Xatolik yuz berdi. Qayta urining.")


# ─── Aloqa ────────────────────────────────────────────────────
@router.message(Command("contact"))
@router.message(F.text == "📞 Aloqa")
async def cmd_contact(message: Message):
    await message.answer(CONTACT_TEXT, parse_mode='HTML')


# ─── Yordam ───────────────────────────────────────────────────
@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "❓ <b>Yordam</b>\n\n"
        "/start — Bosh menu\n"
        "/shop — Do'konni ochish\n"
        "/orders — Buyurtmalarim\n"
        "/promo — Aksiyalar\n"
        "/contact — Aloqa",
        parse_mode='HTML',
    )


# ─── WebApp data ──────────────────────────────────────────────
@router.message(F.web_app_data)
async def handle_web_app_data(message: Message):
    logger.info('WebApp data: %s', message.web_app_data.data[:100])
    await message.answer("✅ Qabul qilindi!")


# ─── Callback: bosh menu ──────────────────────────────────────
@router.callback_query(F.data == 'main_menu')
async def cb_main_menu(callback: CallbackQuery):
    await callback.message.answer(
        "☕ <b>Asl Nurafshon</b>\n\nDo'konni ochish uchun bosing 👇",
        parse_mode='HTML',
        reply_markup=main_menu_keyboard(settings.FRONTEND_URL),
    )
    await callback.answer()


@router.callback_query(F.data == 'contact')
async def cb_contact(callback: CallbackQuery):
    await callback.message.answer(CONTACT_TEXT, parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data == 'my_orders')
async def cb_my_orders(callback: CallbackQuery):
    # /orders handlerini qayta ishlatamiz
    await cmd_orders(callback.message)
    await callback.answer()


# ─── Admin: buyurtma status o'zgartirish ──────────────────────
@router.callback_query(F.data.startswith('order:'))
async def handle_order_callback(callback: CallbackQuery):
    parts = callback.data.split(':')
    if len(parts) != 3:
        await callback.answer("Format xato")
        return

    _, action, order_id_str = parts
    try:
        order_id = int(order_id_str)
    except ValueError:
        await callback.answer("ID xato")
        return

    new_status = STATUS_MAP.get(action)
    if not new_status:
        await callback.answer("Noma'lum amal")
        return

    try:
        from asgiref.sync import sync_to_async
        from apps.orders.models import Order

        @sync_to_async
        def update_order():
            o = Order.objects.select_related('user').get(pk=order_id)
            old = o.status
            o.status = new_status
            o.save(update_fields=['status'])
            return o, old

        order, old_status = await update_order()
    except Exception:
        await callback.answer(f"#{order_id} topilmadi")
        return

    emoji = STATUS_EMOJI.get(new_status, '•')
    label = STATUS_LABEL.get(new_status, new_status)
    await callback.answer(f"{emoji} {label}")

    # Admin xabarini yangilash
    try:
        new_markup = _next_keyboard(order_id, new_status)
        await callback.message.edit_reply_markup(reply_markup=new_markup)
    except Exception:
        pass

    # Mijozga xabar
    from bot.notifications import notify_status_change
    import asyncio
    asyncio.create_task(notify_status_change(order_id, new_status))


def _next_keyboard(order_id: int, status: str):
    if status == 'yolda':
        return order_delivered_keyboard(order_id)
    if status in ('yetkazildi', 'bekor_qilindi'):
        return None
    return order_admin_keyboard(order_id)


# ─── To'lov ───────────────────────────────────────────────────
@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    await message.answer(
        "✅ <b>To'lov qabul qilindi!</b>\n\nXaridingiz uchun rahmat! 🙏",
        parse_mode='HTML',
    )
    if payload.startswith("order_"):
        try:
            order_id = int(payload.split("_")[1])
            from asgiref.sync import sync_to_async
            from apps.orders.models import Order
            o = await sync_to_async(Order.objects.get)(id=order_id)
            if o.payment_status != 'paid':
                o.payment_status = 'paid'
                await sync_to_async(o.save)(update_fields=['payment_status'])
        except Exception as e:
            logger.error("payment update error: %s", e)


# ─── Baholash (feedback) ──────────────────────────────────────
@router.callback_query(F.data.startswith('rate_'))
async def handle_rating(callback: CallbackQuery):
    parts = callback.data.split('_')
    if len(parts) != 3:
        await callback.answer("Format xato")
        return
    try:
        rating = int(parts[1])
        req_id = int(parts[2])
    except ValueError:
        await callback.answer("Xato")
        return

    try:
        from asgiref.sync import sync_to_async
        from apps.orders.models import FeedbackRequest

        @sync_to_async
        def save_r():
            req = FeedbackRequest.objects.get(pk=req_id)
            req.rating = rating
            req.save(update_fields=['rating'])
            return req

        await save_r()
        await callback.answer("⭐ Rahmat!")
        await callback.message.edit_text(
            callback.message.text + f"\n\n{'⭐' * rating} Bahongiz saqlandi.",
            parse_mode='HTML',
        )
    except Exception as e:
        logger.error("rating error: %s", e)
        await callback.answer("Xatolik")
