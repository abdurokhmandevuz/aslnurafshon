import asyncio
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.orders.models import FeedbackRequest
from bot.notifications import _get_bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

class Command(BaseCommand):
    help = 'Sends scheduled feedback request surveys to customers.'

    def handle(self, *args, **options):
        now = timezone.now()
        pending = FeedbackRequest.objects.filter(is_sent=False, scheduled_time__lte=now)
        
        if not pending.exists():
            self.stdout.write("No pending feedback requests.")
            return

        async def process_requests():
            bot = _get_bot()
            if not bot:
                return

            for req in pending:
                try:
                    # Keyboard with 1-5 stars
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [
                            InlineKeyboardButton(text="⭐ 1", callback_data=f"rate_1_{req.id}"),
                            InlineKeyboardButton(text="⭐ 2", callback_data=f"rate_2_{req.id}"),
                            InlineKeyboardButton(text="⭐ 3", callback_data=f"rate_3_{req.id}"),
                        ],
                        [
                            InlineKeyboardButton(text="⭐ 4", callback_data=f"rate_4_{req.id}"),
                            InlineKeyboardButton(text="⭐ 5", callback_data=f"rate_5_{req.id}"),
                        ]
                    ])

                    text = (
                        f"😊 <b>Hurmatli mijoz!</b>\n\n"
                        f"Siz yaqinda buyurtma <b>#{req.order_id}</b> ni qabul qildingiz.\n"
                        f"Xizmatimizdan mamnunmisiz? Iltimos, sifatimizni oshirish uchun o'z bahoyingizni bering:"
                    )
                    
                    await bot.send_message(
                        chat_id=req.order.user.telegram_id,
                        text=text,
                        reply_markup=keyboard,
                        parse_mode='HTML'
                    )
                    req.is_sent = True
                    req.save(update_fields=['is_sent'])
                    self.stdout.write(f"Sent feedback survey for order #{req.order_id} to user {req.order.user.telegram_id}")
                except Exception as exc:
                    self.stderr.write(f"Failed to send feedback for order #{req.order_id}: {exc}")

            await bot.session.close()

        loop = asyncio.get_event_loop()
        loop.run_until_complete(process_requests())
