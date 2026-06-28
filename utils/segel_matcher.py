"""
utils/segel_matcher.py — Logika analisa dan split segel SJ1 + SJ2
Filosofi: OCR baca semua segel → gabung → deduplikasi → split 2+2 → operator konfirmasi.
1 baris Sheets = 1 LO = 2 segel (kolom J & K).
"""

from dataclasses import dataclass, field


@dataclass
class SegelResult:
    status: str                  # "MATCH" | "PARTIAL" | "WARNING"
    segel_sj1: list              # 2 segel untuk baris SJ1 (kolom J & K)
    segel_sj2: list              # 2 segel untuk baris SJ2 (kolom J & K)
    semua_segel: list            # semua segel unik hasil gabungan
    pesan: str                   # teks untuk ditampilkan ke operator
    perlu_konfirmasi: bool       # selalu True — operator wajib konfirmasi


def match_segel(segel_sj1_raw: list, segel_sj2_raw: list) -> SegelResult:
    """
    Analisa segel dari 2 SJ dan tentukan split yang disarankan.

    Kasus yang ditangani:
    A: SJ1=[1,2,3,4] SJ2=[3,4]     → unik=[1,2,3,4] → split 1,2 | 3,4
    B: SJ1=[1,2]     SJ2=[3,4]     → unik=[1,2,3,4] → split 1,2 | 3,4
    C: SJ1=[1,2,3,4] SJ2=[1,2,3,4] → unik=[1,2,3,4] → split 1,2 | 3,4
    D: Kasus tidak normal           → WARNING, operator tentukan manual
    """
    s1 = _normalize(segel_sj1_raw)
    s2 = _normalize(segel_sj2_raw)

    # Gabung semua segel, deduplikasi, pertahankan urutan
    semua = _deduplikasi(s1 + s2)
    total = len(semua)

    # ── Kasus normal: 4 segel unik → split 2+2 ────────────────────────────────
    if total == 4:
        segel_sj1 = semua[0:2]
        segel_sj2 = semua[2:4]

        # Tentukan status berdasarkan kondisi input
        if len(s1) == 4 and len(s2) == 4 and set(s1) == set(s2):
            status = "PARTIAL"
            keterangan = "Kedua SJ memiliki 4 segel sama (depot pisah muatan)."
        elif len(s1) == 4 and len(s2) == 2:
            status = "PARTIAL"
            keterangan = "SJ1 punya 4 segel, SJ2 punya 2 segel lanjutan."
        elif len(s1) == 2 and len(s2) == 2:
            status = "MATCH"
            keterangan = "Masing-masing SJ sudah punya 2 segel sendiri."
        elif len(s1) == 4 and len(s2) == 4 and set(s1) != set(s2):
            status = "MATCH"
            keterangan = "Gabungan 8 segel → deduplikasi → 4 segel unik."
        else:
            status = "PARTIAL"
            keterangan = "Segel digabung dan dideduplikasi."

        pesan = (
            f"Segel {status}\n"
            f"{keterangan}\n\n"
            f"Segel OCR SJ1 : {_fmt(s1)}\n"
            f"Segel OCR SJ2 : {_fmt(s2)}\n"
            f"Semua unik    : {_fmt(semua)}\n\n"
            f"Saran split:\n"
            f"SJ1 (J,K) → {_fmt(segel_sj1)}\n"
            f"SJ2 (J,K) → {_fmt(segel_sj2)}\n\n"
            f"Apakah split ini benar?"
        )

        return SegelResult(
            status=status,
            segel_sj1=segel_sj1,
            segel_sj2=segel_sj2,
            semua_segel=semua,
            pesan=pesan,
            perlu_konfirmasi=True,
        )

    # ── Kasus 8 segel berbeda semua (normal penuh) ────────────────────────────
    if total == 8:
        segel_sj1 = semua[0:2]
        segel_sj2 = semua[4:6]

        pesan = (
            f"Segel MATCH\n"
            f"8 segel unik terbaca.\n\n"
            f"Segel OCR SJ1 : {_fmt(s1)}\n"
            f"Segel OCR SJ2 : {_fmt(s2)}\n\n"
            f"Saran split:\n"
            f"SJ1 (J,K) → {_fmt(segel_sj1)}\n"
            f"SJ2 (J,K) → {_fmt(segel_sj2)}\n\n"
            f"Apakah split ini benar?"
        )

        return SegelResult(
            status="MATCH",
            segel_sj1=segel_sj1,
            segel_sj2=segel_sj2,
            semua_segel=semua,
            pesan=pesan,
            perlu_konfirmasi=True,
        )

    # ── WARNING: jumlah tidak normal ──────────────────────────────────────────
    pesan = (
        f"WARNING - Jumlah segel tidak normal ({total} segel unik).\n\n"
        f"Segel OCR SJ1 : {_fmt(s1)}\n"
        f"Segel OCR SJ2 : {_fmt(s2)}\n"
        f"Semua unik    : {_fmt(semua)}\n\n"
        f"Pilih tindakan."
    )

    return SegelResult(
        status="WARNING",
        segel_sj1=[],
        segel_sj2=[],
        semua_segel=semua,
        pesan=pesan,
        perlu_konfirmasi=True,
    )


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _normalize(segel_list: list) -> list:
    return [s.strip().upper() for s in (segel_list or []) if s and str(s).strip()]


def _deduplikasi(segel_list: list) -> list:
    """Hapus duplikat, pertahankan urutan kemunculan pertama."""
    seen = set()
    result = []
    for s in segel_list:
        if s not in seen:
            seen.add(s)
            result.append(s)
    return result


def _fmt(segel_list: list) -> str:
    return ", ".join(segel_list) if segel_list else "-"
