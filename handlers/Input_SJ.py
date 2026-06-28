"""
handlers/Input_SJ.py — State Machine Input Surat Jalan (STATE 0–7)
"""

import os
import tempfile
import asyncio
from datetime import date, timedelta

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from koneksi import MAIA_API_KEY, get_sheet
from utils.claude_ocr import ocr_surat_jalan, format_ocr_result
from utils.segel_matcher import match_segel
from utils.sheet import push_trip_ke_sheets

router = Router()


class SJState(StatesGroup):
    state0_pilih_tanggal     = State()
    state1_foto_sj1          = State()
    state1b_konfirmasi_sj1   = State()
    state2_tanya_pasangan    = State()
    state3_foto_sj2          = State()
    state4b_konfirmasi_sj2   = State()
    state4_validasi_segel    = State()
    state5_konfirmasi_data   = State()
    state6_konfirmasi_ritase = State()
    state7_kirim_sheets      = State()


def _tombol_tanggal() -> InlineKeyboardMarkup:
    today = date.today()
    buttons = []
    for i in range(6):
        d = today - timedelta(days=i)
        label = f"📅 {d.strftime('%d %b')} {'(Hari ini)' if i == 0 else f'(H-{i})'}"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"tanggal:{d.isoformat()}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _tombol_ya_tidak(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Ya", callback_data=f"{prefix}:ya"),
        InlineKeyboardButton(text="❌ Tidak", callback_data=f"{prefix}:tidak"),
    ]])


def _tombol_konfirmasi_ocr(state_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Data Benar", callback_data=f"ocr_ok:{state_id}")],
        [InlineKeyboardButton(text="✏️ Koreksi Manual", callback_data=f"ocr_koreksi:{state_id}")],
        [InlineKeyboardButton(text="🔄 Kirim Ulang Foto", callback_data=f"ocr_ulang:{state_id}")],
    ])


def _tombol_segel_warning() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Input Manual", callback_data="segel:manual")],
        [InlineKeyboardButton(text="🔄 Ulangi Input SJ", callback_data="segel:ulang")],
    ])


def _tombol_ritase() -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text=f"Trip ke-{i}", callback_data=f"ritase:{i}")]
               for i in range(1, 7)]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def _proses_foto_sj(message: Message, state: FSMContext, sj_key: str):
    if not message.photo:
        await message.answer("⚠️ Kirim foto Surat Jalan ya, bukan teks atau file lain.")
        return

    await message.answer("⏳ Memproses foto dengan Claude Vision API...")

    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name

    await message.bot.download_file(file.file_path, tmp_path)

    try:
        hasil_ocr = await asyncio.to_thread(ocr_surat_jalan, tmp_path, MAIA_API_KEY)
    except Exception as e:
        await message.answer(f"❌ Gagal proses OCR: {e}\n\nCoba kirim ulang foto.")
        return
    finally:
        await asyncio.to_thread(os.unlink, tmp_path)

    await state.update_data({sj_key: hasil_ocr})

    teks = format_ocr_result(hasil_ocr)
    await message.answer(
        f"📄 Hasil OCR Surat Jalan\n\n{teks}",
        reply_markup=_tombol_konfirmasi_ocr(sj_key),
    )


@router.message(F.text == "📋 Input Surat Jalan")
async def mulai_input_sj(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(SJState.state0_pilih_tanggal)
    await message.answer(
        "📅 Pilih tanggal pengiriman SJ:",
        reply_markup=_tombol_tanggal(),
    )


@router.callback_query(SJState.state0_pilih_tanggal, F.data.startswith("tanggal:"))
async def pilih_tanggal(callback: CallbackQuery, state: FSMContext):
    tanggal = callback.data.split(":")[1]
    await state.update_data(tanggal_pengiriman=tanggal)
    await state.set_state(SJState.state1_foto_sj1)
    await callback.message.edit_text(f"✅ Tanggal dipilih: {tanggal}")
    await callback.message.answer("📸 Kirim foto Surat Jalan pertama:")
    await callback.answer()


@router.message(SJState.state1_foto_sj1)
async def terima_foto_sj1(message: Message, state: FSMContext):
    await _proses_foto_sj(message, state, "sj1")
    await state.set_state(SJState.state1b_konfirmasi_sj1)


@router.callback_query(SJState.state1b_konfirmasi_sj1, F.data == "ocr_ok:sj1")
async def konfirmasi_sj1_ok(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SJState.state2_tanya_pasangan)
    await callback.message.edit_reply_markup()
    await callback.message.answer(
        "✅ SJ ke-1 dikonfirmasi.\n\nApakah ada Surat Jalan pasangan (SJ ke-2)?",
        reply_markup=_tombol_ya_tidak("pasangan"),
    )
    await callback.answer()


@router.callback_query(SJState.state1b_konfirmasi_sj1, F.data == "ocr_ulang:sj1")
async def ulang_foto_sj1(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SJState.state1_foto_sj1)
    await callback.message.edit_reply_markup()
    await callback.message.answer("🔄 Silakan kirim ulang foto SJ ke-1:")
    await callback.answer()


@router.callback_query(SJState.state1b_konfirmasi_sj1, F.data == "ocr_koreksi:sj1")
async def koreksi_sj1(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "✏️ Fitur koreksi manual belum tersedia.\n"
        "Silakan kirim ulang foto atau konfirmasi data apa adanya."
    )
    await callback.answer()


@router.callback_query(SJState.state2_tanya_pasangan, F.data == "pasangan:ya")
async def ada_pasangan(callback: CallbackQuery, state: FSMContext):
    await state.update_data(has_pair=True)
    await state.set_state(SJState.state3_foto_sj2)
    await callback.message.edit_reply_markup()
    await callback.message.answer("📸 Kirim foto Surat Jalan ke-2:")
    await callback.answer()


@router.callback_query(SJState.state2_tanya_pasangan, F.data == "pasangan:tidak")
async def tidak_ada_pasangan(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    sj1 = data.get("sj1", {})
    segel_raw = sj1.get("no_segel") or []
    segel_sj1 = segel_raw[:2]

    await state.update_data(
        has_pair=False,
        sj2=None,
        status_segel="PARTIAL",
        segel_final_sj1=segel_sj1,
        segel_final_sj2=[],
    )
    await state.set_state(SJState.state5_konfirmasi_data)
    await callback.message.edit_reply_markup()
    await _tampilkan_konfirmasi_data(callback.message, state)
    await callback.answer()


@router.message(SJState.state3_foto_sj2)
async def terima_foto_sj2(message: Message, state: FSMContext):
    await _proses_foto_sj(message, state, "sj2")
    await state.set_state(SJState.state4b_konfirmasi_sj2)


@router.callback_query(SJState.state4b_konfirmasi_sj2, F.data == "ocr_ok:sj2")
async def konfirmasi_sj2_ok(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup()
    await state.set_state(SJState.state4_validasi_segel)
    await _jalankan_validasi_segel(callback.message, state)
    await callback.answer()


@router.callback_query(SJState.state4b_konfirmasi_sj2, F.data == "ocr_ulang:sj2")
async def ulang_foto_sj2(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SJState.state3_foto_sj2)
    await callback.message.edit_reply_markup()
    await callback.message.answer("🔄 Silakan kirim ulang foto SJ ke-2:")
    await callback.answer()


@router.callback_query(SJState.state4b_konfirmasi_sj2, F.data == "ocr_koreksi:sj2")
async def koreksi_sj2(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "✏️ Fitur koreksi manual belum tersedia.\n"
        "Silakan kirim ulang foto atau konfirmasi data apa adanya."
    )
    await callback.answer()


async def _jalankan_validasi_segel(message: Message, state: FSMContext):
    data = await state.get_data()
    sj1 = data.get("sj1", {})
    sj2 = data.get("sj2", {})

    hasil = match_segel(sj1.get("no_segel", []), sj2.get("no_segel", []))

    await state.update_data(
        status_segel=hasil.status,
        segel_final_sj1=hasil.segel_sj1,
        segel_final_sj2=hasil.segel_sj2,
    )

    if hasil.status == "WARNING":
        await message.answer(
            f"🔒 Validasi Segel\n\n{hasil.pesan}",
            reply_markup=_tombol_segel_warning(),
        )
    else:
        await message.answer(
            f"🔒 Validasi Segel\n\n{hasil.pesan}\n\nLanjut ke konfirmasi data?",
            reply_markup=_tombol_ya_tidak("segel_lanjut"),
        )


@router.callback_query(SJState.state4_validasi_segel, F.data == "segel_lanjut:ya")
async def segel_lanjut(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup()
    await state.set_state(SJState.state5_konfirmasi_data)
    await _tampilkan_konfirmasi_data(callback.message, state)
    await callback.answer()


@router.callback_query(SJState.state4_validasi_segel, F.data == "segel:manual")
async def segel_manual(callback: CallbackQuery, state: FSMContext):
    await state.update_data(status_segel="MANUAL", segel_final_sj1=[], segel_final_sj2=[])
    await state.set_state(SJState.state5_konfirmasi_data)
    await callback.message.edit_reply_markup()
    await callback.message.answer("✏️ Segel dicatat MANUAL. Lanjut konfirmasi data.")
    await _tampilkan_konfirmasi_data(callback.message, state)
    await callback.answer()


@router.callback_query(SJState.state4_validasi_segel, F.data == "segel:ulang")
async def segel_ulang(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SJState.state1_foto_sj1)
    await state.update_data(sj1=None, sj2=None)
    await callback.message.edit_reply_markup()
    await callback.message.answer("🔄 Input diulang dari awal. Kirim foto SJ ke-1:")
    await callback.answer()


async def _tampilkan_konfirmasi_data(message: Message, state: FSMContext):
    data = await state.get_data()
    sj1 = data.get("sj1", {})
    sj2 = data.get("sj2")
    tanggal = data.get("tanggal_pengiriman", "-")
    status_segel = data.get("status_segel", "-")

    teks = (
        f"📋 Konfirmasi Data Final\n\n"
        f"Tanggal: {tanggal}\n\n"
        f"── SJ ke-1 ──\n"
        f"No. LO  : {sj1.get('nomor_lo', '-')}\n"
        f"Plat    : {sj1.get('no_polisi', '-')}\n"
        f"Produk  : {sj1.get('produk', '-')}\n"
        f"Volume  : {sj1.get('jml_kl', '-')} KL\n"
        f"SPBU    : {sj1.get('tujuan_spbu', '-')}\n"
    )

    if sj2:
        teks += (
            f"\n── SJ ke-2 ──\n"
            f"No. LO  : {sj2.get('nomor_lo', '-')}\n"
            f"Produk  : {sj2.get('produk', '-')}\n"
            f"Volume  : {sj2.get('jml_kl', '-')} KL\n"
            f"SPBU    : {sj2.get('tujuan_spbu', '-')}\n"
        )

    teks += f"\nStatus Segel: {status_segel}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Data Benar, Lanjut", callback_data="data_final:ok")],
        [InlineKeyboardButton(text="🔄 Ulang dari Awal", callback_data="data_final:ulang")],
    ])

    await message.answer(teks, reply_markup=keyboard)


@router.callback_query(SJState.state5_konfirmasi_data, F.data == "data_final:ok")
async def data_final_ok(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SJState.state6_konfirmasi_ritase)
    await callback.message.edit_reply_markup()
    await callback.message.answer(
        "🚛 Ini trip ke berapa hari ini?",
        reply_markup=_tombol_ritase(),
    )
    await callback.answer()


@router.callback_query(SJState.state5_konfirmasi_data, F.data == "data_final:ulang")
async def data_final_ulang(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(SJState.state0_pilih_tanggal)
    await callback.message.edit_reply_markup()
    await callback.message.answer(
        "🔄 Input diulang dari awal.\n\n📅 Pilih tanggal pengiriman:",
        reply_markup=_tombol_tanggal(),
    )
    await callback.answer()


@router.callback_query(SJState.state6_konfirmasi_ritase, F.data.startswith("ritase:"))
async def pilih_ritase(callback: CallbackQuery, state: FSMContext):
    ritase_ke = int(callback.data.split(":")[1])
    data = await state.get_data()

    tanggal = data.get("tanggal_pengiriman", date.today().isoformat())
    plat = (data.get("sj1") or {}).get("no_polisi", "UNKNOWN")
    trip_id = f"{tanggal.replace('-', '')}-{plat}-T{ritase_ke}"

    await state.update_data(trip_id=trip_id, ritase_ke=ritase_ke)
    await state.set_state(SJState.state7_kirim_sheets)

    await callback.message.edit_reply_markup()
    await callback.message.answer(f"✅ Trip ID: {trip_id}\n\nMengirim ke Google Sheets...")
    await callback.answer()

    await kirim_ke_sheets(callback.message, state)


async def kirim_ke_sheets(message: Message, state: FSMContext):
    data = await state.get_data()

    try:
        ws = await asyncio.to_thread(get_sheet)
        await asyncio.to_thread(push_trip_ke_sheets, ws, data)
        trip_id = data.get("trip_id", "-")
        ritase_ke = data.get("ritase_ke", "-")
        sj2 = data.get("sj2")

        await message.answer(
            f"✅ Data berhasil disimpan ke Google Sheets!\n\n"
            f"Trip ID : {trip_id}\n"
            f"Ritase  : Trip ke-{ritase_ke}\n"
            f"Baris   : {'2 baris (SJ1 + SJ2)' if sj2 else '1 baris (SJ tunggal)'}"
        )
    except Exception as e:
        await message.answer(
            f"❌ Gagal kirim ke Sheets!\n\n{e}\n\nCoba lagi atau hubungi admin."
        )

    await state.clear()
