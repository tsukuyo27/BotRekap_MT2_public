"""
main.py — Entry point BotRekap_MT
Daftarkan semua router dan middleware, lalu jalankan polling.
"""

import asyncio
import logging

from aiogram import Dispatcher
from aiogram.types import BotCommand

from koneksi import bot, dp, ALLOWED_USERS
from middleware.whitelist import WhitelistMiddleware, RateLimitMiddleware
from handlers import MenuUtama, Input_SJ

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def set_bot_commands():
    await bot.set_my_commands([
        BotCommand(command="start", description="Menu utama"),
    ])


async def main():
    logger.info("BotRekap_MT starting...")

    # ── Middleware (urutan: outer → inner) ─────────────────────────────────────
    dp.message.middleware(WhitelistMiddleware(ALLOWED_USERS))
    dp.callback_query.middleware(WhitelistMiddleware(ALLOWED_USERS))
    dp.message.middleware(RateLimitMiddleware(rate_limit_seconds=2.0))

    # ── Daftarkan router ───────────────────────────────────────────────────────
    dp.include_router(MenuUtama.router)
    dp.include_router(Input_SJ.router)
    # handlers/Laporan_OA.py TIDAK diregister (dormant, sesuai desain v2.0)

    # ── Set bot commands ───────────────────────────────────────────────────────
    await set_bot_commands()

    logger.info(f"Whitelist users: {ALLOWED_USERS}")
    logger.info("Bot is running. Press Ctrl+C to stop.")

    # ── Start polling ──────────────────────────────────────────────────────────
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
