import io
import streamlit as st
import pandas as pd
from engine import hisab_ghurub

st.set_page_config(page_title="KawakibCalc — Hisab Rukyat Digital", layout="wide")

st.title("🌙 KawakibCalc v1.0")
st.caption("Aplikasi Web Hisab Posisi Bulan & Visibilitas Hilal — Kawakib Institute | Terinspirasi dari MoonCalc 6.0 (Dr. Monzur Ahmed)")

# Sampel Markaz Indonesia (dapat diperluas menjadi CSV/JSON 182 kota)
MARKAZ_INDONESIA = [
    ("Sabang", 5.8942, 95.3214, 10, 7.0),
    ("Banda Aceh", 5.5483, 95.3238, 10, 7.0),
    ("Medan", 3.5952, 98.6722, 25, 7.0),
    ("Padang", -0.9471, 100.4172, 10, 7.0),
    ("Jakarta", -6.1751, 106.8272, 10, 7.0),
    ("Semarang", -6.9838, 110.4100, 10, 7.0),
    ("Yogyakarta", -7.7956, 110.3695, 110, 7.0),
    ("Surabaya", -7.2575, 112.7521, 10, 7.0),
    ("Pontianak", -0.0263, 109.3425, 10, 7.0),
    ("Denpasar", -8.6705, 115.2126, 20, 8.0),
    ("Makassar", -5.1477, 119.4327, 10, 8.0),
    ("Kupang", -10.1772, 123.6070, 20, 8.0),
    ("Manado", 1.4748, 124.8421, 15, 8.0),
    ("Ambon", -3.6954, 128.1814, 15, 9.0),
    ("Jayapura", -2.5916, 140.6690, 20, 9.0),
    ("Merauke", -8.4932, 140.4018, 10, 9.0),
]

with st.sidebar:
    st.header("Pengaturan Hisab")
    tgl = st.date_input("Tanggal Pengamatan (Ghurub)")
    refraksi = st.checkbox("Koreksi Refraksi Atmosfer", value=True)
    mode = st.radio("Mode Perhitungan", ["1. Markaz Tunggal", "2. Pemindaian Massal Indonesia"])

if mode == "1. Markaz Tunggal":
    col1, col2, col3, col4 = st.columns(4)
    nama_kota = col1.text_input("Nama Markaz", "Semarang")
    lat = col2.number_input("Lintang (+LU / -LS)", value=-6.9838, format="%.4f")
    lon = col3.number_input("Bujur (+BT / -BB)", value=110.4100, format="%.4f")
    elev = col4.number_input("Elevasi (mdpl)", value=10.0)
    tz = st.selectbox("Zona Waktu", [7.0, 8.0, 9.0], format_func=lambda x: f"UTC+{int(x)}")

    if st.button("Hitung Data Ghurub", type="primary"):
        hasil = hisab_ghurub(nama_kota, lat, lon, elev, tz, tgl.year, tgl.month, tgl.day, refraksi)
        st.subheader(f"Hasil Hisab saat Ghurub — {nama_kota} ({tgl})")
        st.json(hasil)

else:
    st.subheader(f"Rekap Visibilitas Hilal Indonesia — {tgl}")
    if st.button("Jalankan Pemindaian Indonesia", type="primary"):
        baris = [
            hisab_ghurub(nama, lat, lon, elev, tz, tgl.year, tgl.month, tgl.day, refraksi)
            for nama, lat, lon, elev, tz in MARKAZ_INDONESIA
        ]
        df = pd.DataFrame(baris)
        st.dataframe(df, use_container_width=True)

        # Ringkasan Ekstrem Terendah & Tertinggi
        c1, c2 = st.columns(2)
        terendah = df.loc[df["Tinggi_Hilal_Deg"].idxmin()]
        tertinggi = df.loc[df["Tinggi_Hilal_Deg"].idxmax()]
        c1.info(f"**Tinggi Terendah:** {terendah['Kota']} ({terendah['Tinggi_Hilal_Deg']}° | Elongasi {terendah['Elongasi_Geo_Deg']}°)")
        c2.success(f"**Tinggi Tertinggi:** {tertinggi['Kota']} ({tertinggi['Tinggi_Hilal_Deg']}° | Elongasi {tertinggi['Elongasi_Geo_Deg']}°)")

        # Tombol Unduh Excel
        buf = io.BytesIO()
        df.to_excel(buf, index=False, engine="openpyxl")
        st.download_button(
            label="📥 Unduh Rekap Excel (.xlsx)",
            data=buf.getvalue(),
            file_name=f"KawakibCalc_Indonesia_{tgl}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
