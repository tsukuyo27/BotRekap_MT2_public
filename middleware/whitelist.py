"""
middleware/whitelist.py — Keamanan: Whitelist user + rate limiting
Wajib diimplementasi sebelum production (Bab 10 SavePoint v2.0).
"""

import time
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message


class WhitelistMiddleware(BaseMiddleware):
    """
    Blokir semua pesan dari user yang tidak ada di ALLOWED_USERS.
    """

    def __init__(self, allowed_users: list[int]):
        self.allowed_users = allowed_users
        super().__init__()

    async def __call__(self, handler, event: TelegramObject, data: dict):
        # Ambil user dari event
        message = data.get("event_update")
        user = None

        if hasattr(event, "from_user"):
            user = event.from_user
        elif hasattr(event, "message") and event.message:
            user = event.message.from_user

        if user and user.id not in self.allowed_users:
            # Silent reject — tidak balas apa-apa
            return

        return await handler(event, data)


class RateLimitMiddleware(BaseMiddleware):
    """
    Rate limiting sederhana: maks 1 pesan per 2 detik per user.
    Mencegah spam/flood ke bot.
    """

    def __init__(self, rate_limit_seconds: float = 2.0):
        self.rate_limit = rate_limit_seconds
        self._last_message: dict[int, float] = {}
        super().__init__()

    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = None
        if hasattr(event, "from_user"):
            user = event.from_user

        if user:
            now = time.monotonic()
            last = self._last_message.get(user.id, 0)
            if now - last < self.rate_limit:
                # Terlalu cepat — abaikan
                return
            self._last_message[user.id] = now

        return await handler(event, data)
