"""
Telegram bot handlers for Nurafshon.

Handles:
  - /start command  →  main menu with WebApp button
  - web_app_data    →  data sent by the Mini App via Telegram.WebApp.sendData()
  - Callback queries from admin group inline buttons (order status changes)
"""
import logging
import os
import django

# ─── Django setup (must happen before importing Django models) ────────────────
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from django.conf import settings
from aiogram import F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import CallbackQuery, Message, WebAppData, PreCheckoutQuery

from bot.keyboards import (
    main_menu_keyboard,
    order_admin_keyboard,
    order_delivered_keyboard,
)

logger = logging.getLogger(__name__)
router = Router()

# ─── /start ──────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user

    # DB ga saqlash — keyinchalik saytda ishlatamiz
    from asgiref.sync import sync_to_async
    from apps.accounts.models import TelegramUser

    full_name = ' '.join(filter(None, [user.first_name, user.last_name]))

    @sync_to_async
    def save_user():
        TelegramUser.objects.update_or_create(
            telegram_id=user.id,
            defaults={
                'full_name': full_name or str(user.id),
                'username': user.username or '',
                'language_code': user.language_code or 'uz',
            }
        )

    await save_user()
    logger.info('User saved to DB: %s (%s)', full_name, user.id)

    await message.answer(
        f'Assalomu alaykum, <b>{user.first_name}</b>! 👋\n\n'
        f'☕ <b>Nurafshon</b> — sifatli choy va kofe do\'koniga xush kelibsiz!\n\n'
        f"Quydagi tugmani bosib do'konni oching 👇",
        parse_mode='HTML',
        reply_markup=main_menu_keyboard(settings.FRONTEND_URL),
    )


# ─── WebApp data ──────────────────────────────────────────────────────────────

@router.message(F.web_app_data)
async def handle_web_app_data(message: Message):
    """
    Receives data sent by the Mini App via Telegram.WebApp.sendData().
    The Mini App can send JSON payload (e.g., order confirmation).
    """
    data: WebAppData = message.web_app_data
    logger.info('WebApp data from %s: %s', message.from_user.id, data.data)
    # Currently informational — order creation is done via REST API directly.
    await message.answer("✅ Ma'lumot qabul qilindi!")


# ─── "Buyurtmalarim" button ───────────────────────────────────────────────────

@router.callback_query(F.data == 'my_orders')
async def cmd_my_orders(callback: CallbackQuery):
    await callback.message.answer(
        "📦 Buyurtmalaringizni ko'rish uchun do'konni oching:",
        reply_markup=main_menu_keyboard(settings.FRONTEND_URL),
    )
    await callback.answer()


# ─── Admin group callback queries ─────────────────────────────────────────────

@router.callback_query(F.data.startswith('order:'))
async def handle_order_callback(callback: CallbackQuery):
    """
    Callback data format: order:<action>:<order_id>
    Actions: confirm | dispatch | delivered | cancel
    """
    parts = callback.data.split(':')
    if len(parts) != 3:
        await callback.answer("Noto'g'ri format")
        return

    _, action, order_id_str = parts
    try:
        order_id = int(order_id_str)
    except ValueError:
        await callback.answer('Xato ID')
        return

    STATUS_MAP = {
        'confirm': 'tayyorlanmoqda',
        'dispatch': 'yolda',
        'delivered': 'yetkazildi',
        'cancel': 'bekor_qilindi',
    }

    new_status = STATUS_MAP.get(action)
    if not new_status:
        await callback.answer("Noma'lum amal")
        return

    try:
        from apps.orders.models import Order
        order = Order.objects.select_related('user').get(pk=order_id)
    except Order.DoesNotExist:
        await callback.answer(f'Buyurtma #{order_id} topilmadi')
        return

    old_status = order.status
    order.status = new_status
    order.save(update_fields=['status'])

    # Track the change for signal-based notification
    order.tracker_status = old_status  # used in signals.py

    label = dict(Order.Status.choices).get(new_status, new_status)
    await callback.answer(f"✅ Holat o'zgardi: {label}")

    # Update admin message
    action_user = callback.from_user.full_name
    try:
        await callback.message.edit_text(
            callback.message.text + f"\n\n✏️ <b>{action_user}</b> tomonidan o'zgartirildi: <b>{label}</b>",
            parse_mode='HTML',
            reply_markup=_remaining_keyboard(order_id, new_status),
        )
    except Exception:
        pass  # Message may not be editable

    # Notify customer
    from bot.notifications import notify_status_change
    import asyncio
    asyncio.create_task(notify_status_change(order_id, new_status))


def _remaining_keyboard(order_id: int, current_status: str):
    """Return appropriate keyboard after status change."""
    if current_status == 'yolda':
        return order_delivered_keyboard(order_id)
    if current_status in ('yetkazildi', 'bekor_qilindi'):
        return None  # No more actions
    return order_admin_keyboard(order_id)


# ─── Payments ────────────────────────────────────────────────────────────────

@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    """Confirm payment readiness."""
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    """Handle successful payment from Telegram."""
    payload = message.successful_payment.invoice_payload
    if payload.startswith("order_"):
        try:
            order_id = int(payload.split("_")[1])
            from asgiref.sync import sync_to_async
            from apps.orders.models import Order
            
            # Buyurtmani topamiz va to'langan deb belgilaymiz
            order = await sync_to_async(Order.objects.get)(id=order_id)
            if order.payment_status != 'paid':
                order.payment_status = 'paid'
                await sync_to_async(order.save)(update_fields=['payment_status'])
                
                # Mijozga minnatdorchilik
                await message.answer(
                    f"✅ <b>To'lov qabul qilindi!</b>\n\nBuyurtma raqami: <b>#{order.id}</b>\nXaridingiz uchun rahmat!",
                    parse_mode='HTML'
                )
                
                # Adminga xabar berish
                admin_group = settings.ADMIN_GROUP_ID
                if admin_group:
                    await message.bot.send_message(
                        chat_id=admin_group,
                        text=f"✅ <b>Buyurtma #{order.id} to'landi (Click orqali)</b>\n\nXaridor: {message.from_user.full_name}",
                        parse_mode='HTML'
                    )
        except Exception as e:
            logger.error("Error processing successful payment: %s", e)
            await message.answer("To'lov qabul qilindi, lekin tizimda xatolik yuz berdi. Iltimos, admin bilan bog'laning.")


# ─── Feedback Rating Callback ─────────────────────────────────────────────────

@router.callback_query(F.data.startswith('rate_'))
async def handle_feedback_rating_callback(callback: CallbackQuery):
    """
    Callback data format: rate_<rating_value>_<feedback_request_id>
    E.g. rate_5_42
    """
    parts = callback.data.split('_')
    if len(parts) != 3:
        await callback.answer("Noto'g'ri format")
        return

    _, rating_str, req_id_str = parts
    try:
        rating = int(rating_str)
        req_id = int(req_id_str)
    except ValueError:
        await callback.answer('Xato format')
        return

    from asgiref.sync import sync_to_async
    from apps.orders.models import FeedbackRequest

    @sync_to_async
    def save_rating():
        try:
            req = FeedbackRequest.objects.select_related('order__user').get(pk=req_id)
            req.rating = rating
            req.save(update_fields=['rating'])
            return req
        except FeedbackRequest.DoesNotExist:
            return None

    req = await save_rating()
    if not req:
        await callback.answer("Baholash so'rovi topilmadi")
        return

    await callback.answer("Rahmat! Bahongiz qabul qilindi.")
    await callback.message.edit_text(
        callback.message.text + f"\n\n⭐️ <b>Sizning bahoingiz: {rating} yulduz</b>\n\nFikr-mulohazangiz bo'lsa, ushbu xabarga <b>Javob berish (Reply)</b> orqali yozib yuboring (matn ko'rinishida) 👇",
        parse_mode='HTML'
    )


# ─── Feedback Comment Reply Handler ───────────────────────────────────────────

@router.message(F.text & F.reply_to_message)
async def handle_feedback_comment(message: Message):
    reply = message.reply_to_message
    if reply.text and ("bahoyingizni bering" in reply.text or "Sizning bahoingiz" in reply.text):
        from asgiref.sync import sync_to_async
        from apps.orders.models import FeedbackRequest

        @sync_to_async
        def save_comment(telegram_id, text):
            try:
                req = FeedbackRequest.objects.filter(
                    order__user__telegram_id=telegram_id,
                    is_sent=True
                ).select_related('order__user').order_by('-created_at').first()
                if req and not req.comment:
                    req.comment = text
                    req.save(update_fields=['comment'])
                    return req
            except Exception:
                pass
            return None

        req = await save_comment(message.from_user.id, message.text)
        if req:
            await message.reply("Fikringiz uchun rahmat! Tizimga saqlandi. 😊")
            
            # Also notify admin group about the feedback!
            admin_group = settings.ADMIN_GROUP_ID
            if admin_group:
                stars = "⭐" * req.rating if req.rating else "Bahosiz"
                await message.bot.send_message(
                    chat_id=admin_group,
                    text=(
                        f"💬 <b>YANGI FIKR-MULOHAZA (Buyurtma #{req.order_id})</b>\n\n"
                        f"Mijoz: <b>{req.order.user.full_name}</b>\n"
                        f"Bahosi: <b>{stars}</b>\n"
                        f"Izoh: <i>\"{message.text}\"</i>"
                    ),
                    parse_mode='HTML'
                )


# ─── /chek Command ────────────────────────────────────────────────────────────

@router.message(Command("chek"))
@router.message(F.text.lower().in_(['chek', '/chek', 'chekni yuklash']))
async def cmd_chek(message: Message):
    from asgiref.sync import sync_to_async
    from apps.orders.models import Order
    from apps.orders.utils import generate_receipt_pdf
    from aiogram.types import FSInputFile

    @sync_to_async
    def get_latest_order(telegram_id):
        order = Order.objects.filter(user__telegram_id=telegram_id, status='yetkazildi').select_related('user', 'address').prefetch_related('items').order_by('-created_at').first()
        if not order:
            order = Order.objects.filter(user__telegram_id=telegram_id).select_related('user', 'address').prefetch_related('items').order_by('-created_at').first()
        return order

    order = await get_latest_order(message.from_user.id)
    if not order:
        await message.answer("Sizda hali buyurtmalar mavjud emas.")
        return

    try:
        @sync_to_async
        def run_pdf_generation(o):
            return generate_receipt_pdf(o)

        pdf_path = await run_pdf_generation(order)
        await message.reply_document(
            document=FSInputFile(pdf_path, filename=f"chek_order_{order.id}.pdf"),
            caption=f"🧾 Sizning oxirgi buyurtmangiz (#{order.id}) uchun chek."
        )
    except Exception as exc:
        logger.error('Error generating PDF on /chek command for user %s: %s', message.from_user.id, exc)
        await message.answer("Chekni shakllantirishda xatolik yuz berdi. Iltimos keyinroq qayta urinib ko'ring.")
