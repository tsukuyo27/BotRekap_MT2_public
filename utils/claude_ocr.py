"""
utils/claude_ocr.py — Pemanggil Claude Vision API untuk OCR Surat Jalan
Output: dict JSON terstruktur + photo_assessment dalam 1 API call.
Sesuai desain SavePoint v2.0 Bab 7.
"""

import base64
import json
import os
from openai import OpenAI

SYSTEM_PROMPT = 'Kamu adalah sistem OCR untuk Surat Jalan BBM Pertamina. Tugasmu membaca foto Surat Jalan dan mengekstrak data ke format JSON. Selalu kembalikan HANYA JSON, tanpa teks lain, tanpa markdown backticks.'

USER_PROMPT = """Baca Surat Jalan Pertamina dalam foto ini dan ekstrak ke JSON:
{
  "no_polisi": "...",
  "tanggal_pengiriman": "YYYY-MM-DD",
  "jam_keluar": "HH:MM:SS",
  "nomor_lo": "...",
  "nomor_so": "...",
  "shipment_no": "...",
  "nama_pengemudi": "...",
  "tujuan_spbu": "SPBU XXXXXXX",
  "tujuan_lokasi": "...",
  "nama_pt": "...",
  "produk": "...",
  "jml_kl": 0.0,
  "no_segel": ["N-XXXXXXX"],
  "cetakan_ke": 1,
  "photo_assessment": {
    "kejelasan": "JELAS",
    "field_diragukan": [],
    "catatan": null
  }
}

Aturan ekstraksi:
- no_segel: selalu array, ambil SEMUA segel yang ada
- produk: nama standar (BIOSOLAR B40 / PERTALITE / PERTAMAX / DEXLITE)
- jml_kl: angka desimal (misal 8.0)
- Jika field tidak terbaca, isi null
- Tanggal format YYYY-MM-DD, jam format HH:MM:SS

Aturan photo_assessment:
- kejelasan: JELAS / CUKUP / KURANG
- field_diragukan: list nama field yang tidak yakin
- catatan: alasan singkat atau null"""

BADGE_MAP = {
    'JELAS': ('🟢 Foto Jelas', 'Silakan cek dan konfirmasi data berikut.'),
    'CUKUP': ('🟡 Perlu Perhatian', 'Cek lebih teliti field yang diragukan.'),
    'KURANG': ('🔴 Foto Kurang Jelas', 'Disarankan kirim ulang foto yang lebih jelas.')
}

def ocr_surat_jalan(image_path: str, api_key: str) -> dict:
    """
    Proses foto SJ dengan Claude via MAIA Router (OpenAI-compatible).
    """
    client = OpenAI(api_key=api_key, base_url='https://api.maiarouter.ai/v1')
    
    with open(image_path, 'rb') as f:
        image_data = base64.standard_b64encode(f.read()).decode('utf-8')
        
    _, ext = os.path.splitext(image_path)
    ext = ext.lower()
    
    media_type_map = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.webp': 'image/webp'
    }
    media_type = media_type_map.get(ext, 'image/jpeg')
    
    response = client.chat.completions.create(
        model='anthropic/claude-sonnet-4-6',
        messages=[
            {
                'role': 'system',
                'content': SYSTEM_PROMPT
            },
            {
                'role': 'user',
                'content': [
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': f'data:{media_type};base64,{image_data}'
                        }
                    },
                    {
                        'type': 'text',
                        'text': USER_PROMPT
                    }
                ]
            }
        ],
        max_tokens=1000
    )
    
    raw_text = response.choices[0].message.content.strip()
    
    # Strip markdown code blocks if any
    if raw_text.startswith('```'):
        raw_text = raw_text.split('```')[1]
        if raw_text.startswith('json'):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()
        
    try:
        result = json.loads(raw_text)
        return result
    except json.JSONDecodeError as e:
        raise ValueError(f"Model tidak mengembalikan JSON valid: {e}\nRaw: {raw_text}")


def format_badge(photo_assessment: dict) -> tuple[str, str]:
    """
    Kembalikan (badge_text, pesan_ke_operator) berdasarkan photo_assessment.
    Default ke CUKUP jika nilai kejelasan tidak dikenali.
    """
    pa = photo_assessment if photo_assessment else {}
    kejelasan = pa.get('kejelasan', 'CUKUP').upper()
    return BADGE_MAP.get(kejelasan, BADGE_MAP['CUKUP'])


def format_ocr_result(data: dict) -> str:
    """
    Format hasil OCR menjadi teks ringkasan untuk ditampilkan ke operator di STATE 1b.
    """
    pa = data.get('photo_assessment', {})
    badge_text, badge_msg = format_badge(pa)
    
    field_diragukan = pa.get('field_diragukan', [])
    catatan = pa.get('catatan')
    
    segel_list = data.get('no_segel')
    segel_str = ', '.join(segel_list) if segel_list else '-'
    
    lines = [
        f"{badge_text} — {badge_msg}",
        "",
        f"🚛 Plat       : {data.get('no_polisi') or '-'}",
        f"📅 Tanggal    : {data.get('tanggal_pengiriman') or '-'}",
        f"🕐 Jam Keluar : {data.get('jam_keluar') or '-'}",
        f"📋 No. LO     : {data.get('nomor_lo') or '-'}",
        f"🏪 SPBU       : {data.get('tujuan_spbu') or '-'}",
        f"⛽ Produk     : {data.get('produk') or '-'}",
        f"📦 Volume     : {data.get('jml_kl') or '-'} KL",
        f"🔒 Segel      : {segel_str}",
        f"👤 Pengemudi  : {data.get('nama_pengemudi') or '-'}"
    ]
    
    if field_diragukan:
        lines.append(f"\n⚠️ Field diragukan: {', '.join(field_diragukan)}")
    if catatan:
        lines.append(f"📝 Catatan Claude: {catatan}")
        
    return '\n'.join(lines)


# =========================================================================
# === 🔹 LEGACY GAS CODE (BACKUP - COMMENTED OUT) ===
# =========================================================================
# // =========================================================================
# // === 🔹 1. CONFIG & KONSTANTA GLOBAL ===
# // =========================================================================
# 
# const CONFIG = {
#   SHEET_REPORTA: "ReportA",
#   SHEET_SEGEL: "DBSegel",
#   SHEET_REPORTB: "ReportB",
#   SHEET_SETUP: "Setup Awal V2",
#   SLIDE_TEMPLATE_ID: "1950HSlvSv0weXhQ7IiAWFaOeuhK2SRTHIlnQJ00KgMw",
#   PDF_FOLDER_ID: "1KdpwBcigIAnvbvrtK2Jr9fl8l4tnE_qS"
# };
# 
# const PROCESSING_KEY = "BATCH_PROCESSING";
# const PARAM_COL = 2;
# const FLAG_COL = 21;
# 
# const ADM_DOK = {
#   START_ROW: 14,
#   END_ROW:   19,
#   COL_NAMA:  5,   // Kolom E
#   COL_STATUS:6,   // Kolom F
#   COL_EXPIRED:7,  // Kolom G
#   DOCS: ['STNK', 'Pajak', 'KEUR', 'TERA', 'IZIN B3', 'KP B3']
# };
# 
# // =========================================================================
# // === 🔹 2. TRIGGER & UI (Antarmuka) ===
# // =========================================================================
# 
# function onOpen() {
#   const ui = SpreadsheetApp.getUi();
#   ui.createMenu('📌 TOOLS')
#     .addSubMenu(
#       ui.createMenu('⚙️ SETUP')
#         .addItem('📋 Panel Setup', 'openSetupPanel')
#     )
#     .addSubMenu(
#       ui.createMenu('✅ VALIDATE & PROCESS')
#         .addItem('📄 Batch DBSegel', 'executeBatchProcess')
#     )
#     .addSubMenu(
#       ui.createMenu('🛠️ UTILITIES')
#         .addItem('🔐 Grant Authorizations', 'grantAuthorizations')
#     )
#     .addToUi();
# }
# 
# function openSetupPanel() {
#   const html = HtmlService.createHtmlOutputFromFile('Sidebar')
#     .setTitle('⚙️ SETUP PANEL V5');
#   SpreadsheetApp.getUi().showSidebar(html);
# }
# 
# // =========================================================================
# // === 🔹 3. MODUL ARMADA & SDM (ARSITEKTUR BARU - BLOK 1) ===
# // =========================================================================
# 
# /**
#  * Mengambil data gabungan Armada dan SDM untuk mempercepat loading form HTML
#  */
# function getDatabaseTerpadu() {
#   const ss = SpreadsheetApp.getActiveSpreadsheet();
#   
#   // 1. Get Data AMT (SDM)
#   const dbAMT = ss.getSheetByName("DataBaseAMT");
#   let listAMT = [];
#   if (dbAMT) {
#     const lastRowAMT = dbAMT.getLastRow();
#     if (lastRowAMT >= 4) {
#       const valsAMT = dbAMT.getRange(4, 2, lastRowAMT - 3, 7).getValues();
#       valsAMT.forEach(r => {
#         if (r[0]) {
#           listAMT.push({
#             id: String(r[0]).trim(),
#             nama: String(r[1]).trim(),
#             transportir: String(r[6]).trim() // Kolom H (Transportir)
#           });
#         }
#       });
#     }
#   }
# 
#   // 2. Get Data Armada (MT)
#   const dbMT = ss.getSheetByName("DataBaseMT");
#   let listArmada = [];
#   if (dbMT) {
#     const lastRowMT = dbMT.getLastRow();
#     if (lastRowMT >= 4) {
#       // B sampai J (9 Kolom)
#       const valsMT = dbMT.getRange(4, 2, lastRowMT - 3, 9).getValues();
#       
#       const safeDate = (val) => {
#         if (!val) return "";
#         if (Object.prototype.toString.call(val) === '[object Date]') {
#           return Utilities.formatDate(val, ss.getSpreadsheetTimeZone(), "yyyy-MM-dd");
#         }
#         return String(val).trim();
#       };
# 
#       valsMT.forEach((r, idx) => {
#         if (r[0]) {
#           listArmada.push({
#             row: idx + 4,
#             plat: String(r[0]).trim(),
#             sk: String(r[1]).trim(),
#             status: String(r[2]).trim(),
#             tgl_stnk: safeDate(r[3]),
#             tgl_keur: safeDate(r[4]),
#             tgl_tera: safeDate(r[5]),
#             tgl_pajak: safeDate(r[6]),
#             amt1: String(r[7]).trim(),
#             amt2: String(r[8]).trim()
#           });
#         }
#       });
#     }
#   }
# 
#   return { armada: listArmada, amt: listAMT };
# }
# 
# /**
#  * Menyimpan data Armada (Otomatis deteksi Update atau Insert)
#  */
# function saveDataArmada(data) {
#   const ss = SpreadsheetApp.getActiveSpreadsheet();
#   const dbMT = ss.getSheetByName("DataBaseMT");
#   if (!dbMT) throw new Error("Tab DataBaseMT tidak ditemukan!");
# 
#   const rowData = [
#     data.plat, data.sk, data.status, 
#     data.tgl_stnk, data.tgl_keur, data.tgl_tera, data.tgl_pajak, 
#     data.amt1, data.amt2
#   ];
# 
#   if (data.mode !== 'NEW') {
#     // UPDATE DATA EKSISTING
#     const allPlat = dbMT.getRange(1, 2, dbMT.getMaxRows(), 1).getValues();
#     let targetRow = -1;
#     for (let i = 3; i < allPlat.length; i++) {
#       if (String(allPlat[i][0]).toUpperCase() === data.mode.toUpperCase()) {
#         targetRow = i + 1;
#         break;
#       }
#     }
#     if (targetRow === -1) throw new Error("Data lama tidak ditemukan untuk diupdate.");
#     
#     dbMT.getRange(targetRow, 2, 1, 9).setValues([rowData]);
#     return { message: "Data berhasil diperbarui!" };
#     
#   } else {
#     // INSERT DATA BARU
#     const allPlat = dbMT.getRange(1, 2, dbMT.getMaxRows(), 1).getValues();
#     let targetRow = -1;
#     for (let i = 3; i < allPlat.length; i++) {
#       if (String(allPlat[i][0]).toUpperCase() === data.plat) {
#         throw new Error("Plat nomor sudah terdaftar! Gunakan fitur edit.");
#       }
#       if (allPlat[i][0] === "" && targetRow === -1) {
#         targetRow = i + 1; 
#       }
#     }
#     
#     if (targetRow === -1) targetRow = dbMT.getLastRow() + 1;
#     if (targetRow < 4) targetRow = 4;
# 
#     dbMT.getRange(targetRow, 2, 1, 9).setValues([rowData]);
#     return { message: "Armada baru berhasil ditambahkan!" };
#   }
# }
# 
# /**
#  * Menghapus Armada
#  */
# function hapusDataArmada(plat) {
#   const ss = SpreadsheetApp.getActiveSpreadsheet();
#   const dbMT = ss.getSheetByName("DataBaseMT");
#   
#   const allPlat = dbMT.getRange(1, 2, dbMT.getMaxRows(), 1).getValues();
#   for (let i = 3; i < allPlat.length; i++) {
#     if (String(allPlat[i][0]).toUpperCase() === plat.toUpperCase()) {
#       dbMT.deleteRow(i + 1);
#       return { message: "Armada dihapus permanen!" };
#     }
#   }
#   throw new Error("Plat tidak ditemukan.");
# }
# 
# // =========================================================================
# // === 🔹 4. MODUL BULANAN, VENDOR & CONFIG (SETUP AWAL V2) ===
# // =========================================================================
# 
# function loadBulanData() {
#   const ss = SpreadsheetApp.getActiveSpreadsheet();
#   const setupSheet = ss.getSheetByName(CONFIG.SHEET_SETUP);
#   if (!setupSheet) return {}; 
# 
#   let tglTagihRaw = setupSheet.getRange('B8').getValue();
#   let tglTagihFormatted = '';
#   
#   if (Object.prototype.toString.call(tglTagihRaw) === '[object Date]') {
#     tglTagihFormatted = Utilities.formatDate(tglTagihRaw, ss.getSpreadsheetTimeZone(), "yyyy-MM-dd");
#   } else {
#     tglTagihFormatted = tglTagihRaw; 
#   }
# 
#   return {
#     bulan_nomor: setupSheet.getRange('B2').getValue(), 
#     tahun: setupSheet.getRange('B4').getValue(),
#     periode_awal: setupSheet.getRange('B5').getValue(),
#     periode_akhir: setupSheet.getRange('B6').getValue(),
#     tgl_tagih: tglTagihFormatted,
#     harga_ownuse: setupSheet.getRange('B9').getValue(),
#     no_po: setupSheet.getRange('B10').getValue()
#   };
# }
# 
# function saveBulanData(data) {
#   PropertiesService.getScriptProperties().setProperty('BULAN_DATA', JSON.stringify(data));
#   writeSetupToSheet(data, 'BULAN');
# }
# 
# function loadVendorData() {
#   const ss = SpreadsheetApp.getActiveSpreadsheet();
#   const setupSheet = ss.getSheetByName(CONFIG.SHEET_SETUP);
#   if (!setupSheet) return {};
#   return {
#     nama_vendor:  setupSheet.getRange('F2').getValue(),
#     no_apms:      setupSheet.getRange('F3').getValue(),
#     no_vendor:    setupSheet.getRange('F4').getValue(),
#     email_vendor: setupSheet.getRange('F5').getValue(),
#     no_hp:        setupSheet.getRange('F6').getValue(),
#     nama_surat:   setupSheet.getRange('F7').getValue(),
#     supply_point: setupSheet.getRange('F8').getValue()
#   };
# }
# 
# function saveVendorData(data) {
#   PropertiesService.getScriptProperties().setProperty('VENDOR_DATA', JSON.stringify(data));
#   writeSetupToSheet(data, 'VENDOR');
# }
# 
# function loadConfigData() {
#   const ss = SpreadsheetApp.getActiveSpreadsheet();
#   const setupSheet = ss.getSheetByName(CONFIG.SHEET_SETUP);
#   if (!setupSheet) return {};
#   return {
#     slide_id: setupSheet.getRange('B1').getValue(),
#     pdf_folder_id: setupSheet.getRange('B2').getValue() 
#   };
# }
# 
# function saveConfigData(data) {
#   PropertiesService.getScriptProperties().setProperty('CONFIG_DATA', JSON.stringify(data));
#   if (data.slide_id) CONFIG.SLIDE_TEMPLATE_ID = data.slide_id;
#   if (data.pdf_folder_id) CONFIG.PDF_FOLDER_ID = data.pdf_folder_id;
#   writeSetupToSheet(data, 'CONFIG');
# }
# 
# // =========================================================================
# // === 🔹 5. MODUL ADMINISTRASI DOKUMEN (Legacy di Setup Awal V2) ===
# // =========================================================================
# 
# function loadAdmDokData() {
#   const ss = SpreadsheetApp.getActiveSpreadsheet();
#   const setupSheet = ss.getSheetByName(CONFIG.SHEET_SETUP);
#   if (!setupSheet) throw new Error(`Sheet "${CONFIG.SHEET_SETUP}" tidak ditemukan`);
# 
#   const result = [];
#   for (let row = ADM_DOK.START_ROW; row <= ADM_DOK.END_ROW; row++) {
#     const nama = String(setupSheet.getRange(row, ADM_DOK.COL_NAMA).getValue() || '').trim();
#     const status = String(setupSheet.getRange(row, ADM_DOK.COL_STATUS).getDisplayValue() || '').trim();
#     const expired = String(setupSheet.getRange(row, ADM_DOK.COL_EXPIRED).getDisplayValue() || '').trim();
#     result.push({ nama, status, expired, row });
#   }
#   return result;
# }
# 
# function saveAdmDokData(data) {
#   const ss = SpreadsheetApp.getActiveSpreadsheet();
#   const setupSheet = ss.getSheetByName(CONFIG.SHEET_SETUP);
#   if (!setupSheet) throw new Error(`Sheet "${CONFIG.SHEET_SETUP}" tidak ditemukan`);
# 
#   const nama    = String(data.nama    || '').trim();
#   const expired = String(data.expired || '').trim();
# 
#   if (!nama)    throw new Error('Nama dokumen wajib diisi');
#   if (!expired) throw new Error('Tanggal expired wajib diisi');
#   if (!/^\d{2}\/\d{2}\/\d{4}$/.test(expired)) {
#     throw new Error('Format tanggal harus DD/MM/YYYY, contoh: 20/08/2027');
#   }
# 
#   let targetRow = null;
#   for (let row = ADM_DOK.START_ROW; row <= ADM_DOK.END_ROW; row++) {
#     const cellNama = String(setupSheet.getRange(row, ADM_DOK.COL_NAMA).getValue() || '').trim();
#     if (cellNama.toLowerCase() === nama.toLowerCase()) {
#       targetRow = row;
#       break;
#     }
#   }
# 
#   if (!targetRow) throw new Error(`Dokumen "${nama}" tidak ditemukan di sheet`);
# 
#   const expiredCell = setupSheet.getRange(targetRow, ADM_DOK.COL_EXPIRED);
#   expiredCell.setNumberFormat('@STRING@');
#   expiredCell.setValue(expired);           
# 
#   const statusCell    = setupSheet.getRange(targetRow, ADM_DOK.COL_STATUS);
#   const currentFormula = statusCell.getFormula();
#   if (!currentFormula) {
#     statusCell.setFormula(buildStatusFormula(`G${targetRow}`));
#   }
# 
#   SpreadsheetApp.flush();
#   return { success: true, message: `Expired ${nama} diperbarui → ${expired}` };
# }
# 
# // =========================================================================
# // === 🔹 6. HELPER & UTILITIES ===
# // =========================================================================
# 
# function writeSetupToSheet(data, type) {
#   const ss = SpreadsheetApp.getActiveSpreadsheet();
#   const setupSheet = ss.getSheetByName(CONFIG.SHEET_SETUP);
#   if (!setupSheet) throw new Error(`Sheet "${CONFIG.SHEET_SETUP}" tidak ditemukan`);
# 
#   if (type === 'BULAN') {
#     let tglTagihFormatted = '';
#     if (data.tgl_tagih) {
#       const parts = String(data.tgl_tagih).split('-');
#       if (parts.length === 3) {
#         tglTagihFormatted = `'${parts[2]}-${parts[1]}-${parts[0]}`;
#       } else {
#         tglTagihFormatted = data.tgl_tagih;
#       }
#     }
# 
#     const cellMap = {
#       'B2':  parseInt(data.bulan_nomor) || '',
#       'B4':  parseInt(data.tahun)       || '',
#       'B5':  parseInt(data.periode_awal)  || '',
#       'B6':  parseInt(data.periode_akhir) || '',
#       'B8':  tglTagihFormatted, 
#       'B9':  parseFloat(data.harga_ownuse) || '',
#       'B10': String(data.no_po || '').trim()
#     };
#     Object.entries(cellMap).forEach(([cell, value]) => {
#       setupSheet.getRange(cell).setValue(value);
#     });
#   } else if (type === 'VENDOR') {
#     const cellMap = {
#       'F2': data.nama_vendor,
#       'F3': data.no_apms,
#       'F4': data.no_vendor,
#       'F5': data.email_vendor,
#       'F6': data.no_hp,
#       'F7': data.nama_surat,
#       'F8': data.supply_point
#     };
#     Object.entries(cellMap).forEach(([cell, value]) => {
#       if (value !== undefined && value !== '') {
#         setupSheet.getRange(cell).setValue(value);
#       }
#     });
#   }
# }
# 
# function buildStatusFormula(expiredCell) {
#   const tgl =
#     `IF(ISNUMBER(${expiredCell}),` +
#       `${expiredCell},` +
#       `DATEVALUE(MID(${expiredCell},4,2)&"/"&LEFT(${expiredCell},2)&"/"&RIGHT(${expiredCell},4))` +
#     `)`;
#   const sisa = `${tgl}-TODAY()`;
#  
#   return `=IF(${expiredCell}="","—",` +
#     `IFERROR(` +
#       `LET(` +
#         `tgl,${tgl},` +
#         `sisa,tgl-TODAY(),` +
#         `IF(sisa<=0,` +
#           `"❌ Non Aktif — Harus Perpanjang",` +
#         `IF(sisa<=7,` +
#           `"🚨 Aktif — Sisa "&TEXT(sisa,"0")&" Hari (Warning Kritis)",` +
#         `IF(sisa<=15,` +
#           `"🔶 Aktif — Sisa "&TEXT(sisa,"0")&" Hari (Warning 2)",` +
#         `IF(sisa<=30,` +
#           `"⚠️ Aktif — Sisa "&TEXT(sisa,"0")&" Hari (Warning 1)",` +
#           `"✅ Aktif — Sisa "&TEXT(sisa,"0")&" Hari"` +
#         `))))` +
#       `)` +
#     `,"❌ Error baca tanggal")` +
#   `)`;
# }
# 
# function initAdmDokFormulas() {
#   const ss = SpreadsheetApp.getActiveSpreadsheet();
#   const setupSheet = ss.getSheetByName(CONFIG.SHEET_SETUP);
#   if (!setupSheet) {
#     SpreadsheetApp.getUi().alert('❌ Sheet "' + CONFIG.SHEET_SETUP + '" tidak ditemukan.');
#     return;
#   }
#  
#   let berhasil = 0;
#   for (let row = ADM_DOK.START_ROW; row <= ADM_DOK.END_ROW; row++) {
#     try {
#       setupSheet.getRange(row, ADM_DOK.COL_STATUS).setFormula(buildStatusFormula(`G${row}`));
#       berhasil++;
#     } catch (e) {
#       console.error(`❌ Baris ${row}:`, e.toString());
#     }
#   }
#  
#   SpreadsheetApp.flush();
#   SpreadsheetApp.getUi().alert(`✅ Formula dipasang ke ${berhasil} baris.`);
# }
