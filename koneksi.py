"""
koneksi.py — Inisialisasi semua koneksi external BotRekap_MT
Diimport oleh modul lain yang butuh akses ke bot, sheets, atau Claude API.
"""

import os
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

# Load environment variables dari config.env
load_dotenv("config.env")

# === Telegram ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_USERS_RAW = os.getenv("ALLOWED_USERS", "")
ALLOWED_USERS = [int(uid.strip()) for uid in ALLOWED_USERS_RAW.split(",") if uid.strip()]

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# === Claude API ===
MAIA_API_KEY = os.getenv("MAIA_API_KEY")

# === Google Sheets ===
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SHEET_NAME = os.getenv("SHEET_NAME", "ReportA")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def get_sheet():
    """Buka koneksi ke Google Sheets dan return worksheet ReportA."""
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    return spreadsheet.worksheet(SHEET_NAME)
