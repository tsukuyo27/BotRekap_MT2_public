"""
handlers/MenuUtama.py — Menu utama Telegram Bot (v2.0)
2 menu saja: Input Surat Jalan + Catatan Perubahan.
Laporan OA dihapus dari Telegram (digantikan GAS Web App F5).
Sesuai desain SavePoint v2.0 Bab 5.
"""

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

router = Router()

# ─── Keyboard utama ───────────────────────────────────────────────────────────

MENU_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Input Surat Jalan")],
        [KeyboardButton(text="📝 Catatan Perubahan")],
    ],
    resize_keyboard=True,
    persistent=True,
)

CATATAN_PERUBAHAN = (
    "📝 Catatan Perubahan\n"
    "\n"
    "v2.0 - 12 Mei 2026\n"
    "- Menu Input SJ menggantikan semua menu input lama\n"
    "- Laporan OA dipindah ke GAS Web App\n"
    "- OCR menggunakan Claude Vision API\n"
    "- Foto SJ fisik dan screenshot Android didukung\n"
    "\n"
    "v1.0 - 09 Mei 2026\n"
    "- Rilis awal sistem BotRekap MT"
)

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Selamat datang di BotRekap MT\n\nPilih menu:",
        reply_markup=MENU_KEYBOARD,
    )

@router.message(F.text == "📝 Catatan Perubahan")
async def menu_catatan(message: Message):
    await message.answer(CATATAN_PERUBAHAN)
