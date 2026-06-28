"""
utils/sheet.py — Push data SJ ke Google Sheets ReportA
Append 2 baris per trip (1 baris per SJ). Kolom A, F, L-O dikosongkan (diisi GAS).
Sesuai skema kolom SavePoint v2.0 Bab 4.
"""

from datetime import datetime


# Urutan kolom yang DIISI bot: B, C, D, E, G, H, I, J, K, P, Q, R, S, T
# Kolom A (No Urut) = auto GAS
# Kolom F (APMS), L-O (tanggal pecah, State) = auto GAS saat klik Validasi
# Total kolom A-T = 20 kolom


def _buat_baris(
    timestamp: str,        # B — waktu bot append
    tanggal_sj: str,       # C — tanggal aktual SJ (YYYY-MM-DD)
    no_lo: str,            # D
    no_apms: str,          # E — kode APMS (dari tujuan_spbu)
    plat_no: str,          # G
    produk: str,           # H
    qty_kl: float,         # I
    segel_utama: str,      # J — segel pertama
    segel_lanjutan: str,   # K — segel kedua
    trip_id: str,          # P
    ritase_ke: int,        # Q
    pasangan_lo: str,      # R — LO pasangan, kosong jika SJ tunggal
    status_segel: str,     # S — MATCH / PARTIAL / MANUAL
    metode_input: str,     # T — SJ_FOTO / SS / MANUAL
) -> list:
    """
    Susun 1 baris sebagai list 20 elemen (kolom A-T).
    Kolom yang dikosongkan: A (index 0), F (index 5), L-O (index 11-14).
    """
    row = [""] * 20  # A-T = 20 kolom

    row[1]  = timestamp        # B
    row[2]  = tanggal_sj       # C
    row[3]  = no_lo            # D
    row[4]  = no_apms          # E
    # row[5] F — kosong, diisi GAS
    row[6]  = plat_no          # G
    row[7]  = produk           # H
    row[8]  = qty_kl           # I
    row[9]  = segel_utama      # J
    row[10] = segel_lanjutan   # K
    # row[11-14] L-O — kosong, diisi GAS
    row[15] = trip_id          # P
    row[16] = ritase_ke        # Q
    row[17] = pasangan_lo      # R
    row[18] = status_segel     # S
    row[19] = metode_input     # T

    return row


def push_trip_ke_sheets(worksheet, fsm_data: dict) -> bool:
    """
    Append 2 baris ke Google Sheets untuk 1 trip (SJ1 + SJ2).
    Jika trip hanya 1 SJ, append 1 baris saja.

    Args:
        worksheet: gspread Worksheet object dari koneksi.get_sheet()
        fsm_data: dict state FSM yang sudah final (STATE 7)

    Returns:
        True jika berhasil.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sj1 = fsm_data["sj1"]
    sj2 = fsm_data.get("sj2")  # None jika SJ tunggal
    trip_id = fsm_data["trip_id"]
    ritase_ke = fsm_data["ritase_ke"]
    status_segel = fsm_data["status_segel"]
    segel_sj1 = fsm_data.get("segel_final_sj1", ["", ""])
    segel_sj2 = fsm_data.get("segel_final_sj2", ["", ""])

    # Ambil kode APMS dari field tujuan_spbu (contoh: "SPBU 65743003" → "65743003")
    def parse_apms(tujuan_spbu: str) -> str:
        if not tujuan_spbu:
            return ""
        parts = tujuan_spbu.strip().split()
        return parts[-1] if parts else tujuan_spbu

    # ── Baris SJ1 ──────────────────────────────────────────────────────────────
    baris_sj1 = _buat_baris(
        timestamp=timestamp,
        tanggal_sj=fsm_data["tanggal_pengiriman"],
        no_lo=sj1.get("nomor_lo", ""),
        no_apms=parse_apms(sj1.get("tujuan_spbu", "")),
        plat_no=sj1.get("no_polisi", ""),
        produk=sj1.get("produk", ""),
        qty_kl=sj1.get("jml_kl", 0.0),
        segel_utama=segel_sj1[0] if len(segel_sj1) > 0 else "",
        segel_lanjutan=segel_sj1[1] if len(segel_sj1) > 1 else "",
        trip_id=trip_id,
        ritase_ke=ritase_ke,
        pasangan_lo=sj2.get("nomor_lo", "") if sj2 else "",
        status_segel=status_segel,
        metode_input="SJ_FOTO",
    )
    worksheet.append_row(baris_sj1, value_input_option="USER_ENTERED", table_range="A1")

    # ── Baris SJ2 (jika ada) ───────────────────────────────────────────────────
    if sj2:
        baris_sj2 = _buat_baris(
            timestamp=timestamp,
            tanggal_sj=fsm_data["tanggal_pengiriman"],
            no_lo=sj2.get("nomor_lo", ""),
            no_apms=parse_apms(sj2.get("tujuan_spbu", "")),
            plat_no=sj2.get("no_polisi", sj1.get("no_polisi", "")),
            produk=sj2.get("produk", ""),
            qty_kl=sj2.get("jml_kl", 0.0),
            segel_utama=segel_sj2[0] if len(segel_sj2) > 0 else "",
            segel_lanjutan=segel_sj2[1] if len(segel_sj2) > 1 else "",
            trip_id=trip_id,
            ritase_ke=ritase_ke,
            pasangan_lo=sj1.get("nomor_lo", ""),
            status_segel=status_segel,
            metode_input="SJ_FOTO",
        )
        worksheet.append_row(baris_sj2, value_input_option="USER_ENTERED", table_range="A1")

    return True
