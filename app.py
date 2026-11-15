import io
from datetime import datetime, time, date
import streamlit as st
import pandas as pd
from engine import (
    deg_to_dms,
    ra_to_hms,
    hisab_lengkap_markaz,
    hisab_ghurub,
    susun_baris_rekap_kemenag,
    hitung_gerhana_tahunan,
)

st.set_page_config(page_title="KawakibCalc — Hisab Rukyat Digital", page_icon="🌙", layout="wide")

st.title("🌙 KawakibCalc v1.2")
st.caption(
    "Aplikasi Web Hisab Posisi Bulan, Visibilitas Hilal & Rekap Sinkronisasi — Kawakib Institute | "
    "Terinspirasi dari MoonCalc 6.0 (Dr. Monzur Ahmed)"
)

# 46 Markaz Provinsi, Lokasi Rukyat Utama & Titik Ekstrem Indonesia
MARKAZ_INDONESIA = [
    ("Sabang (Titik Barat)", 5.8942, 95.3214, 10, 7.0),
    ("Banda Aceh (Lhoknga)", 5.4650, 95.2430, 10, 7.0),
    ("Lhokseumawe", 5.1801, 97.1507, 10, 7.0),
    ("Medan", 3.5952, 98.6722, 25, 7.0),
    ("Padang", -0.9471, 100.4172, 10, 7.0),
    ("Pekanbaru", 0.5071, 101.4478, 20, 7.0),
    ("Tanjungpinang", 0.9186, 104.4665, 15, 7.0),
    ("Jambi", -1.6101, 103.6131, 20, 7.0),
    ("Palembang", -2.9761, 104.7754, 10, 7.0),
    ("Bengkulu", -3.7928, 102.2608, 15, 7.0),
    ("Bandar Lampung", -5.4292, 105.2611, 30, 7.0),
    ("Pangkalpinang", -2.1316, 106.1169, 15, 7.0),
    ("Serang (Anyer)", -6.0715, 105.8842, 10, 7.0),
    ("Jakarta (Ancol)", -6.1256, 106.8380, 10, 7.0),
    ("Pelabuhan Ratu", -6.9867, 106.5444, 15, 7.0),
    ("Bandung", -6.9175, 107.6191, 700, 7.0),
    ("Observatorium Bosscha", -6.8247, 107.6158, 1310, 7.0),
    ("Semarang (UIN Walisongo)", -6.9918, 110.3482, 50, 7.0),
    ("Yogyakarta (Parangtritis)", -8.0258, 110.3331, 15, 7.0),
    ("Gresik (Bukit Condrodipo)", -7.1697, 112.6186, 120, 7.0),
    ("Surabaya", -7.2575, 112.7521, 10, 7.0),
    ("Banyuwangi (Alas Purwo)", -8.6500, 114.3667, 10, 7.0),
    ("Pontianak", -0.0263, 109.3425, 10, 7.0),
    ("Palangkaraya", -2.2136, 113.9108, 25, 7.0),
    ("Banjarmasin", -3.3186, 114.5944, 10, 8.0),
    ("Samarinda", -0.5022, 117.1536, 15, 8.0),
    ("Tanjung Selor", 2.8375, 117.3653, 15, 8.0),
    ("Denpasar", -8.6705, 115.2126, 20, 8.0),
    ("Mataram", -8.5833, 116.1167, 30, 8.0),
    ("Kupang", -10.1772, 123.6070, 20, 8.0),
    ("Pulau Rote (Titik Selatan)", -10.7333, 123.1167, 15, 8.0),
    ("Makassar", -5.1477, 119.4327, 10, 8.0),
    ("Mamuju", -2.6748, 118.8885, 15, 8.0),
    ("Palu", -0.8917, 119.8707, 20, 8.0),
    ("Kendari", -3.9985, 122.5130, 20, 8.0),
    ("Gorontalo", 0.5435, 123.0568, 15, 8.0),
    ("Manado", 1.4748, 124.8421, 15, 8.0),
    ("Pulau Miangas (Titik Utara)", 5.5564, 126.5839, 10, 8.0),
    ("Ternate", 0.7893, 127.3771, 20, 9.0),
    ("Ambon", -3.6954, 128.1814, 15, 9.0),
    ("Sorong", -0.8762, 131.2558, 15, 9.0),
    ("Manokwari", -0.8615, 134.0620, 15, 9.0),
    ("Biak", -1.1767, 136.0820, 15, 9.0),
    ("Jayapura", -2.5916, 140.6690, 20, 9.0),
    ("Wamena", -4.0983, 138.9489, 1650, 9.0),
    ("Merauke (Titik Timur)", -8.4932, 140.4018, 10, 9.0),
]

# Paket Tanggal 29 Sesuai Sheet Kemenag
PAKET_1448H = [
    ("Ramadan 1448 H", datetime(2027, 2, 7)),
    ("Syawal 1448 H", datetime(2027, 3, 8)),
    ("Zulhijah 1448 H", datetime(2027, 5, 6)),
]

PAKET_2028M = [
    ("Ramadan 1449 H", datetime(2028, 1, 27)),
    ("Syawal 1449 H", datetime(2028, 2, 25)),
    ("Zulkaidah 1449 H", datetime(2028, 3, 26)),
    ("Zulhijah 1449 H", datetime(2028, 4, 24)),
    ("Muharam 1450 H", datetime(2028, 5, 24)),
    ("Safar 1450 H", datetime(2028, 6, 22)),
    ("Rabiulawal 1450 H", datetime(2028, 7, 22)),
    ("Rabiulakhir 1450 H", datetime(2028, 8, 20)),
    ("Jumadilawal 1450 H", datetime(2028, 9, 19)),
    ("Jumadilakhir 1450 H", datetime(2028, 10, 18)),
    ("Rajab 1450 H", datetime(2028, 11, 17)),
    ("Syakban 1450 H", datetime(2028, 12, 16)),
]

with st.sidebar:
    st.header("Pengaturan Hisab")
    tgl = st.date_input("Tanggal Pengamatan")
    jam_pilihan = st.time_input("Jam Waktu Pilihan (Layar 1)", value=time(18, 0, 0))
    refraksi = st.checkbox("Koreksi Refraksi Atmosfer", value=True)
    mode = st.radio(
        "Pilih Menu KawakibCalc",
        [
            "1. Tabel Ringkasan Markaz (4 Layar)",
            "2. Pemindaian Massal Indonesia",
            "3. Rekap Format Sinkronisasi Kemenag",
            "4. Daftar Gerhana Tahunan",
        ],
    )

# ==============================================================================
# MODE 1: TABEL RINGKASAN MARKAZ (ALA 4 LAYAR MOONCALC 6.0)
# ==============================================================================
if mode == "1. Tabel Ringkasan Markaz (4 Layar)":
    pilihan_preset = st.selectbox(
        "Pilih Cepat Markaz Indonesia (atau isi manual di bawah)",
        ["-- Input Manual --"] + [m[0] for m in MARKAZ_INDONESIA],
    )

    def_nama, def_lat, def_lon, def_elev, def_tz = "Semarang (UIN Walisongo)", -6.9918, 110.3482, 50.0, 7.0
    if pilihan_preset != "-- Input Manual --":
        for m in MARKAZ_INDONESIA:
            if m[0] == pilihan_preset:
                def_nama, def_lat, def_lon, def_elev, def_tz = m[0], m[1], m[2], float(m[3]), m[4]
                break

    c1, c2, c3, c4, c5 = st.columns([2, 1.2, 1.2, 1, 1])
    nama_kota = c1.text_input("Nama Markaz", value=def_nama)
    lat = c2.number_input("Lintang (+LU / -LS)", value=def_lat, format="%.4f")
    lon = c3.number_input("Bujur (+BT / -BB)", value=def_lon, format="%.4f")
    elev = c4.number_input("Elevasi (mdpl)", value=def_elev)
    tz_idx = [7.0, 8.0, 9.0].index(def_tz)
    tz = c5.selectbox("Zona Waktu", [7.0, 8.0, 9.0], index=tz_idx, format_func=lambda x: f"UTC+{int(x)}")

    if st.button("Hitung 4 Layar Data Bulan", type="primary"):
        dt_gabung = datetime.combine(tgl, jam_pilihan)
        data = hisab_lengkap_markaz(nama_kota, lat, lon, elev, tz, dt_gabung, refraksi)
        meta = data["meta"]
        l1 = data["layar1_user"]
        l2 = data["layar2_ghurub"]
        l3 = data["layar3_min5"]

        tab1, tab2, tab3, tab4 = st.tabs([
            "Layar 1: Waktu Pilihan",
            "Layar 2: Saat Ghurub",
            "Layar 3: Matahari -5° & Best Time",
            "Layar 4: Ekspor .TXT",
        ])

        with tab1:
            st.subheader(f"Data Posisi Pada Waktu Pilihan ({meta['Waktu_Pilihan']} {meta['Zona_Waktu']})")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Julian Day (UT)", f"{meta['JD_User']}")
            m2.metric("Delta T (TD-UT)", f"{meta['Delta_T_Detik']} dtk")
            m3.metric("Apparent Sunrise", meta["Sunrise"])
            m4.metric("Apparent Sunset", meta["Ghurub"])

            df_l1 = pd.DataFrame([
                {"Parameter": "Tinggi Bulan (Topo)", "Nilai": f"{deg_to_dms(l1['alt_m'])} ({l1['alt_m']:.4f}°)"},
                {"Parameter": "Azimut Bulan", "Nilai": f"{deg_to_dms(l1['az_m'], True)} ({l1['az_m']:.2f}°)"},
                {"Parameter": "Deklinasi & RA Bulan", "Nilai": f"{deg_to_dms(l1['dec_m'])} | {ra_to_hms(l1['ra_m'])}"},
                {"Parameter": "Tinggi Matahari (Topo)", "Nilai": f"{deg_to_dms(l1['alt_s'])} ({l1['alt_s']:.4f}°)"},
                {"Parameter": "Azimut Matahari", "Nilai": f"{deg_to_dms(l1['az_s'], True)} ({l1['az_s']:.2f}°)"},
                {"Parameter": "Elongasi Geosentris / Topo", "Nilai": f"{deg_to_dms(l1['elong_geo'])} / {deg_to_dms(l1['elong_topo'])}"},
                {"Parameter": "Umur Bulan & Iluminasi", "Nilai": f"{l1['umur_jam']} jam | {l1['iluminasi_persen']:.2f}%"},
                {"Parameter": "Lebar Sabit & Semidiameter", "Nilai": f"{l1['lebar_sabit_arcmin']:.3f}′ | SD {l1['sd_moon_arcmin']:.2f}′"},
                {"Parameter": "Moonrise / Moonset", "Nilai": f"{meta['Moonrise']} / {meta['Moonset']} (Lag: {meta['Lag_Menit']} mnt)"},
                {"Parameter": "Ijtimak Terdekat", "Nilai": meta["Ijtimak"]},
                {"Parameter": "Purnama (Istiqbal) Terdekat", "Nilai": meta["Purnama"]},
                {"Parameter": "Perigee & Apogee Terdekat", "Nilai": f"{meta['Perigee']} | {meta['Apogee']}"},
            ])
            st.dataframe(df_l1, use_container_width=True, hide_index=True)

        with tab2:
            st.subheader(f"Data Saat Apparent Sunset / Ghurub ({meta['Ghurub']} {meta['Zona_Waktu']})")
            c_a, c_b, c_c, c_d = st.columns(4)
            c_a.metric("Tinggi Hilal Mar'i", deg_to_dms(l2["alt_m"]), f"{l2['alt_m']:.4f}°")
            c_b.metric("Elongasi Geosentris", deg_to_dms(l2["elong_geo"]), f"{l2['elong_geo']:.4f}°")
            c_c.metric("Muktsul Hilal (Lag)", f"{meta['Lag_Menit']} mnt")
            c_d.metric("Status Neo-MABIMS", l2["Neo_MABIMS"])

            df_l2 = pd.DataFrame([
                {"Parameter": "Kriteria Neo-MABIMS (3° & 6.4°)", "Hasil": l2["Neo_MABIMS"]},
                {"Parameter": "Kriteria Wujudul Hilal", "Hasil": l2["Wujudul_Hilal"]},
                {"Parameter": "Kriteria Yallop (1997)", "Hasil": f"q = {l2['Yallop_q']} → {l2['Yallop_Status']}"},
                {"Parameter": "Kriteria Odeh (2004)", "Hasil": f"V = {l2['Odeh_V']} → {l2['Odeh_Status']}"},
                {"Parameter": "Kriteria Babylonian Klasik", "Hasil": l2["Babylonian"]},
                {"Parameter": "Azimut Matahari / Bulan", "Hasil": f"{deg_to_dms(l2['az_s'], True)} / {deg_to_dms(l2['az_m'], True)}"},
                {"Parameter": "Selisih Azimut (Rel Azi)", "Hasil": deg_to_dms(l2["rel_az"])},
                {"Parameter": "Umur Bulan saat Ghurub", "Hasil": f"{l2['umur_jam']} jam (Ijtimak: {meta['Ijtimak']})"},
                {"Parameter": "Lebar Sabit & Fase", "Hasil": f"{l2['lebar_sabit_arcmin']:.3f}′ ({l2['iluminasi_persen']:.2f}%)"},
            ])
            st.dataframe(df_l2, use_container_width=True, hide_index=True)

        with tab3:
            st.subheader("Data Saat Matahari -5° di Bawah Ufuk & Best Time (Yallop/Bruin)")
            p5 = l3["pos_min5"]
            pb = l3["pos_best"]
            df_l3 = pd.DataFrame([
                {"Parameter": "Waktu Pengamatan", "Matahari -5°": l3["waktu_min5"], "Best Time (Ghurub + 4/9 Lag)": l3["waktu_best"]},
                {"Parameter": "Tinggi Bulan (Topo)", "Matahari -5°": deg_to_dms(p5["alt_m"]), "Best Time (Ghurub + 4/9 Lag)": deg_to_dms(pb["alt_m"])},
                {"Parameter": "Azimut Bulan", "Matahari -5°": deg_to_dms(p5["az_m"], True), "Best Time (Ghurub + 4/9 Lag)": deg_to_dms(pb["az_m"], True)},
                {"Parameter": "Tinggi Matahari", "Matahari -5°": deg_to_dms(p5["alt_s"]), "Best Time (Ghurub + 4/9 Lag)": deg_to_dms(pb["alt_s"])},
                {"Parameter": "Elongasi Geosentris", "Matahari -5°": deg_to_dms(p5["elong_geo"]), "Best Time (Ghurub + 4/9 Lag)": deg_to_dms(pb["elong_geo"])},
            ])
            st.dataframe(df_l3, use_container_width=True, hide_index=True)

        with tab4:
            teks_laporan = f"""====================================================================
KAWAKIBCALC v1.2 - TABEL DATA HISAB BULAN & HILAL
Kawakib Institute | Inspired by MoonCalc 6.0 by Dr. Monzur Ahmed
====================================================================
Markaz      : {meta['Kota']} (Lat: {meta['Lintang']}, Lon: {meta['Bujur']}, Elev: {meta['Elevasi_m']} m)
Zona Waktu  : {meta['Zona_Waktu']} | Refraksi: {meta['Refraksi']} | Delta T: {meta['Delta_T_Detik']} dtk
Ijtimak     : {meta['Ijtimak']}
App. Sunset : {meta['Ghurub']} | Moonset: {meta['Moonset']} | Lag: {meta['Lag_Menit']} menit
--------------------------------------------------------------------
[AT APPARENT SUNSET / GHURUB]
Tinggi Hilal (Topo)  : {deg_to_dms(l2['alt_m'])} ({l2['alt_m']:.4f} deg)
Elongasi Geosentris  : {deg_to_dms(l2['elong_geo'])} ({l2['elong_geo']:.4f} deg)
Azimut Matahari      : {deg_to_dms(l2['az_s'], True)}
Azimut Bulan         : {deg_to_dms(l2['az_m'], True)}
Umur Bulan           : {l2['umur_jam']} jam
Lebar Sabit          : {l2['lebar_sabit_arcmin']:.3f} arcmin
Status Neo-MABIMS    : {l2['Neo_MABIMS']}
Kriteria Yallop      : q = {l2['Yallop_q']} -> {l2['Yallop_Status']}
Kriteria Odeh        : V = {l2['Odeh_V']} -> {l2['Odeh_Status']}
====================================================================
"""
            st.code(teks_laporan, language="text")
            st.download_button(
                label="📥 Unduh Laporan Teks (.txt)",
                data=teks_laporan,
                file_name=f"KawakibCalc_{nama_kota.replace(' ', '_')}_{tgl}.txt",
                mime="text/plain",
            )

# ==============================================================================
# MODE 2: PEMINDAIAN MASSAL 46 MARKAZ INDONESIA
# ==============================================================================
elif mode == "2. Pemindaian Massal Indonesia":
    st.subheader(f"Rekap Visibilitas Hilal 46 Markaz Indonesia — {tgl}")
    if st.button("Jalankan Pemindaian Indonesia", type="primary"):
        baris = [
            hisab_ghurub(nama, lat, lon, elev, tz, tgl.year, tgl.month, tgl.day, refraksi)
            for nama, lat, lon, elev, tz in MARKAZ_INDONESIA
        ]
        df = pd.DataFrame(baris)

        c1, c2, c3 = st.columns(3)
        terendah = df.loc[df["Tinggi_Deg"].idxmin()]
        tertinggi = df.loc[df["Tinggi_Deg"].idxmax()]
        jml_imkan = int((df["Neo_MABIMS"] == "IMKAN RUKYAT").sum())

        c1.info(f"**Tinggi Terendah:** {terendah['Kota']} ({terendah['Tinggi_DMS']} | Elongasi {terendah['Elongasi_Deg']}°)")
        c2.success(f"**Tinggi Tertinggi:** {tertinggi['Kota']} ({tertinggi['Tinggi_DMS']} | Elongasi {tertinggi['Elongasi_Deg']}°)")
        c3.warning(f"**Imkan Neo-MABIMS:** {jml_imkan} dari {len(df)} markaz")

        st.dataframe(df, use_container_width=True, hide_index=True)

        st.subheader("Peta Sebaran Markaz Pengamatan")
        st.map(df, latitude="Lintang", longitude="Bujur", zoom=3)

        buf = io.BytesIO()
        df.to_excel(buf, index=False, engine="openpyxl")
        st.download_button(
            label="📥 Unduh Rekap Lengkap Excel (.xlsx)",
            data=buf.getvalue(),
            file_name=f"KawakibCalc_46_Markaz_Indonesia_{tgl}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ==============================================================================
# MODE 3: REKAP FORMAT SINKRONISASI KEMENAG (PERSIS KOLOM GOOGLE SHEET)
# ==============================================================================
elif mode == "3. Rekap Format Sinkronisasi Kemenag":
    st.subheader("Rekap Format Google Sheet Sinkronisasi Kemenag (Baris Sistem: Moon Calc)")
    st.info("Kolom °, ′, ″ pada Tinggi dan Elongasi Geosentris sudah dipisah per sel agar tinggal salin-tempel ke Google Sheet Kemenag.")

    paket = st.radio(
        "Pilih Paket Tab Sheet Kemenag:",
        [
            "Tab 1: Rmdn, Sywl, Zul 1448 H (3 Bulan Kunci)",
            "Tab 2: Tahun 2028 M (Ramadan 1449 H – Syakban 1450 H)",
            "Custom: 1 Bulan Tertentu (Sesuai Tanggal di Sidebar)",
        ],
    )

    if st.button("Susun Rekap Format Kemenag", type="primary"):
        if paket.startswith("Tab 1"):
            daftar_target = PAKET_1448H
            nama_file = "Rekap_Kemenag_MoonCalc_1448H.xlsx"
        elif paket.startswith("Tab 2"):
            daftar_target = PAKET_2028M
            nama_file = "Rekap_Kemenag_MoonCalc_2028M.xlsx"
        else:
            daftar_target = [(f"Bulan Target ({tgl})", datetime(tgl.year, tgl.month, tgl.day))]
            nama_file = f"Rekap_Kemenag_MoonCalc_{tgl}.xlsx"

        hasil_rekap = []
        progress = st.progress(0)
        for idx, (nama_bln, dt_29) in enumerate(daftar_target):
            hasil_rekap.append(susun_baris_rekap_kemenag(nama_bln, dt_29, MARKAZ_INDONESIA, refraksi))
            progress.progress((idx + 1) / len(daftar_target))

        df_kemenag = pd.DataFrame(hasil_rekap)
        st.dataframe(df_kemenag, use_container_width=True, hide_index=True)

        buf = io.BytesIO()
        df_kemenag.to_excel(buf, index=False, engine="openpyxl")
        st.download_button(
            label="📥 Unduh Tabel Format Kemenag (.xlsx)",
            data=buf.getvalue(),
            file_name=nama_file,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ==============================================================================
# MODE 4: DAFTAR GERHANA TAHUNAN (MENU 8 MOONCALC)
# ==============================================================================
else:
    st.subheader("Daftar Gerhana Matahari & Bulan Tahunan (Menu 8 MoonCalc)")
    col_y, col_z = st.columns(2)
    tahun_gerhana = col_y.number_input("Tahun Masehi", min_value=1900, max_value=2100, value=tgl.year, step=1)
    tz_gerhana = col_z.selectbox("Zona Waktu Tampilan", [7.0, 8.0, 9.0], format_func=lambda x: f"UTC+{int(x)}")

    if st.button("Hitung Jadwal Gerhana", type="primary"):
        hasil_gerhana = hitung_gerhana_tahunan(int(tahun_gerhana), tz_gerhana)
        if hasil_gerhana:
            st.dataframe(pd.DataFrame(hasil_gerhana), use_container_width=True, hide_index=True)
        else:
            st.info("Tidak ada data gerhana ditemukan pada rentang tersebut.")
