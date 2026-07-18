"""
Bot entry point.

Starts the bot in:
  - Webhook mode if BOT_WEBHOOK_URL env var is set
  - Long-polling mode otherwise (suitable for local dev)

Usage:
    python -m bot.main
"""
import asyncio
import logging
import os
import sys

# ─── Ensure project root is in path ──────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ─── Django must be configured before importing handlers ─────────────────────
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

import django
django.setup()

from django.conf import settings

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from bot.handlers import router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)s %(levelname)s %(message)s',
)
logger = logging.getLogger(__name__)

WEBHOOK_PATH = '/bot/webhook'


async def on_startup(bot: Bot):
    await bot.set_my_commands([
        BotCommand(command='start', description='Bosh menu'),
        BotCommand(command='shop', description="Do'konni ochish"),
        BotCommand(command='orders', description='Buyurtmalarim'),
        BotCommand(command='promo', description='Aksiyalar'),
        BotCommand(command='contact', description='Aloqa'),
        BotCommand(command='chek', description='Oxirgi chek'),
        BotCommand(command='help', description='Yordam'),
    ])
    webhook_url = settings.BOT_WEBHOOK_URL
    if webhook_url:
        full_url = webhook_url.rstrip('/') + WEBHOOK_PATH
        await bot.set_webhook(url=full_url, drop_pending_updates=True)
        logger.info('Webhook set to %s', full_url)
    else:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info('Webhook cleared — running in polling mode')


async def on_shutdown(bot: Bot):
    logger.info('Bot shutting down …')
    await bot.session.close()


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(router)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    return dp


def run_polling():
    """Start bot in long-polling mode (local dev)."""
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = build_dispatcher()
    logger.info('Starting bot in polling mode …')
    asyncio.run(dp.start_polling(bot))


def run_webhook():
    """Start bot behind an aiohttp webhook server."""
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = build_dispatcher()

    app = web.Application()
    handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    port = int(os.environ.get('BOT_PORT', 8443))
    logger.info('Starting bot webhook server on port %d …', port)
    web.run_app(app, host='0.0.0.0', port=port)


if __name__ == '__main__':
    if not settings.BOT_TOKEN:
        logger.error('BOT_TOKEN is not set — cannot start bot')
        sys.exit(1)

    if settings.BOT_WEBHOOK_URL:
        run_webhook()
    else:
        run_polling()
