"""
utils/sheet.py — Push data SJ ke Google Sheets ReportA
Append 1-2 baris per trip.
Kolom E, K-N dikosongkan (menunggu diisi otomatis oleh GAS).
"""

from datetime import datetime
import gspread


def _buat_baris(
    timestamp: str,        # A — waktu bot append
    tanggal_sj: str,       # B — tanggal aktual SJ (YYYY-MM-DD)
    no_lo: str,            # C
    no_apms: str,          # D — kode APMS (dari tujuan_spbu)
    plat_no: str,          # F
    produk: str,           # G
    qty_kl: float,         # H
    segel_utama: str,      # I — segel pertama
    segel_lanjutan: str,   # J — segel kedua
    trip_id: str,          # K
    ritase_ke: int,        # L
    pasangan_lo: str,      # M — LO pasangan, kosong jika SJ tunggal
    status_segel: str,     # N — MATCH / PARTIAL / MANUAL
    metode_input: str,     # O — SJ_FOTO / SS / MANUAL
) -> list:
    """
    Susun 1 baris sebagai list 15 elemen (mewakili Kolom A sampai O).
    Karena API dipanggil dengan table_range="A1", index 0 di sini 
    akan otomatis masuk ke Kolom A di Google Sheets.
    """
    row = [""] * 15  # Array 15 elemen (A hingga O)

    row[0]  = timestamp        # A
    row[1]  = tanggal_sj       # B
    row[2]  = no_lo            # C
    row[3]  = no_apms          # D
    # row[4] mewakili Kolom E — kosong, diisi GAS
    row[5]  = plat_no          # F
    row[6]  = produk           # G
    row[7]  = qty_kl           # H
    row[8]  = segel_utama      # I
    row[9]  = segel_lanjutan   # J
    row[10] = trip_id          # K
    row[11] = ritase_ke        # L
    row[12] = pasangan_lo      # M
    row[13] = status_segel     # N
    row[14] = metode_input     # O

    return row


def push_trip_ke_sheets(worksheet: gspread.Worksheet, fsm_data: dict) -> bool:
    """
    Append baris ke Google Sheets untuk 1 trip (SJ1 + opsional SJ2).
    Menggunakan batch append untuk efisiensi API dan akurasi baris.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Menggunakan .get() agar bot tidak crash jika ada key yang terlewat
    sj1 = fsm_data.get("sj1", {})
    sj2 = fsm_data.get("sj2")  # None jika SJ tunggal
    trip_id = fsm_data.get("trip_id", "")
    ritase_ke = fsm_data.get("ritase_ke", 1)
    status_segel = fsm_data.get("status_segel", "")
    segel_sj1 = fsm_data.get("segel_final_sj1", ["", ""])
    segel_sj2 = fsm_data.get("segel_final_sj2", ["", ""])

    # Ambil kode APMS dari field tujuan_spbu (contoh: "SPBU 65743003" → "65743003")
    def parse_apms(tujuan_spbu: str) -> str:
        if not tujuan_spbu:
            return ""
        parts = tujuan_spbu.strip().split()
        return parts[-1] if parts else tujuan_spbu

    # Siapkan penampung untuk batch insert
    rows_to_append = []

    # ── Baris SJ1 ──────────────────────────────────────────────────────────────
    baris_sj1 = _buat_baris(
        timestamp=timestamp,
        tanggal_sj=fsm_data.get("tanggal_pengiriman", ""),
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
    rows_to_append.append(baris_sj1)

    # ── Baris SJ2 (jika ada) ───────────────────────────────────────────────────
    if sj2:
        baris_sj2 = _buat_baris(
            timestamp=timestamp,
            tanggal_sj=fsm_data.get("tanggal_pengiriman", ""),
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
        rows_to_append.append(baris_sj2)

    # ── Eksekusi Batch Append ──────────────────────────────────────────────────
    try:
        worksheet.append_rows(
            rows_to_append,
            value_input_option="USER_ENTERED",
            insert_data_option="INSERT_ROWS", 
            table_range="A1"  # Penting: Mulai mapping index 0 ke Kolom A
        )
        return True
    except Exception as e:
        print(f"Gagal push ke sheets: {e}")
        return False
