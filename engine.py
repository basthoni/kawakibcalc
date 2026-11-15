import math
from datetime import datetime, timedelta, timezone
import numpy as np
from skyfield.api import load, wgs84
from skyfield import almanac

# Muat epemeris JPL DE421
ts = load.timescale()
eph = load('de421.bsp')
earth, sun, moon = eph['earth'], eph['sun'], eph['moon']


def deg_to_dms(deg: float, is_azimuth: bool = False) -> str:
    """Konversi derajat desimal ke format standar falak (±DD° MM′ SS.S″)."""
    val = float(deg)
    if is_azimuth:
        val = val % 360.0
        sign = ""
    else:
        sign = "-" if val < 0 else "+"
        val = abs(val)
    d = int(val)
    m_full = (val - d) * 60.0
    m = int(m_full)
    s = (m_full - m) * 60.0
    return f"{sign}{d:02d}° {m:02d}′ {s:04.1f}″"


def ra_to_hms(ra_hours: float) -> str:
    """Konversi Asensio Rekta (jam) ke format HHj MMm SS.Ss."""
    val = float(ra_hours) % 24.0
    h = int(val)
    m_full = (val - h) * 60.0
    m = int(m_full)
    s = (m_full - m) * 60.0
    return f"{h:02d}j {m:02d}m {s:04.1f}d"


def ekstrak_waktu(t_arr, ev_arr, target_ev: int) -> list:
    """Mengambil daftar objek Time secara aman baik berbentuk skalar maupun array."""
    if getattr(t_arr, 'shape', ()) == ():
        return [t_arr] if int(ev_arr) == target_ev else []
    return [t_arr[i] for i in range(len(t_arr)) if int(ev_arr[i]) == target_ev]


def hitung_dip_derajat(elevasi_m: float) -> float:
    """Kerendahan ufuk (dip) dalam derajat berdasarkan elevasi pengamat (meter)."""
    if elevasi_m <= 0:
        return 0.0
    return 1.76 * math.sqrt(elevasi_m) / 60.0


def cari_fase_dan_apsis(t_ref):
    """Mencari Ijtimak, Purnama, Perigee, dan Apogee terdekat dalam rentang ±16 hari."""
    t0 = ts.tt_jd(t_ref.tt - 16)
    t1 = ts.tt_jd(t_ref.tt + 16)

    # Konjungsi (1) & Oposisi (0)
    f_conj = almanac.oppositions_conjunctions(eph, moon)
    times, events = almanac.find_discrete(t0, t1, f_conj)
    ijtimak_list = ekstrak_waktu(times, events, 1)
    purnama_list = ekstrak_waktu(times, events, 0)

    t_ijtimak = min(ijtimak_list, key=lambda ti: abs(ti.tt - t_ref.tt)) if ijtimak_list else None
    t_purnama = min(purnama_list, key=lambda ti: abs(ti.tt - t_ref.tt)) if purnama_list else None

    # Perigee & Apogee melalui sampling jarak setiap 15 menit
    jd_grid = np.linspace(t_ref.tt - 15.0, t_ref.tt + 15.0, 2881)
    t_grid = ts.tt_jd(jd_grid)
    dists = earth.at(t_grid).observe(moon).distance().km
    idx_min = int(np.argmin(dists))
    idx_max = int(np.argmax(dists))

    return {
        "ijtimak": t_ijtimak,
        "purnama": t_purnama,
        "perigee": t_grid[idx_min],
        "perigee_km": float(dists[idx_min]),
        "apogee": t_grid[idx_max],
        "apogee_km": float(dists[idx_max]),
    }


def evaluasi_kriteria(alt_topo: float, arcv_geo: float, elong_geo: float,
                      lebar_sabit_arcmin: float, lag_menit: float, umur_jam: float) -> dict:
    """Evaluasi visibilitas hilal: Neo-MABIMS, Wujudul Hilal, Yallop, Odeh, dan Babylonian."""
    # 1. Neo-MABIMS (Tinggi Mar'i >= 3.0 deg & Elongasi Geosentris >= 6.4 deg)
    imkan_mabims = (alt_topo >= 3.0) and (elong_geo >= 6.4)

    # 2. Wujudul Hilal (Tinggi > 0 deg & sudah ijtimak sebelum ghurub)
    wujud = (alt_topo > 0.0) and (umur_jam > 0.0)

    # 3. Yallop (1997) - Parameter q
    w = lebar_sabit_arcmin
    arcv_yallop = 11.8371 - 6.3226 * w + 0.7319 * (w ** 2) - 0.1018 * (w ** 3)
    q = (arcv_geo - arcv_yallop) / 10.0

    if q > 0.216:
        kat_yallop = "A (Mudah terlihat mata telanjang)"
    elif q > -0.014:
        kat_yallop = "B (Terlihat kondisi atmosfer cerah)"
    elif q > -0.160:
        kat_yallop = "C (Perlu alat bantu optik dahulu)"
    elif q > -0.232:
        kat_yallop = "D (Hanya terlihat dengan teleskop)"
    elif q > -0.293:
        kat_yallop = "E (Tidak terlihat teleskop konvensional)"
    else:
        kat_yallop = "F (Di bawah limit Danjon / Mustahil)"

    # 4. Odeh (2004) - Parameter V
    arcv_odeh = -0.1018 * (w ** 3) + 0.7319 * (w ** 2) - 6.3226 * w + 7.1651
    v_odeh = arcv_geo - arcv_odeh
    if v_odeh >= 5.65:
        kat_odeh = "A (Mata telanjang)"
    elif v_odeh >= 2.00:
        kat_odeh = "B (Optik / Mata telanjang kondisi ideal)"
    elif v_odeh >= -0.96:
        kat_odeh = "C (Hanya dengan alat bantu optik)"
    else:
        kat_odeh = "D (Tidak terlihat)"

    # 5. Babylonian Klasik
    babylonian = (umur_jam > 24.0) and (lag_menit > 48.0)

    return {
        "Neo_MABIMS": "IMKAN RUKYAT" if imkan_mabims else "BELUM IMKAN",
        "Wujudul_Hilal": "WUJUD" if wujud else "BELUM WUJUD",
        "Yallop_q": round(float(q), 3),
        "Yallop_Status": kat_yallop,
        "Odeh_V": round(float(v_odeh), 3),
        "Odeh_Status": kat_odeh,
        "Babylonian": "Terlihat" if babylonian else "Tidak Terlihat",
    }


def _ukur_posisi_seketika(observer, t_obj, tekan_mbar: float):
    """Mengukur seluruh parameter toposentris & geosentris pada satu titik waktu t_obj."""
    astro_sun = observer.at(t_obj).observe(sun).apparent()
    astro_moon = observer.at(t_obj).observe(moon).apparent()

    alt_s, az_s, dist_s = astro_sun.altaz(temperature_C=27.0, pressure_mbar=tekan_mbar)
    alt_m, az_m, dist_m = astro_moon.altaz(temperature_C=27.0, pressure_mbar=tekan_mbar)
    ra_s, dec_s, _ = astro_sun.radec()
    ra_m, dec_m, _ = astro_moon.radec()

    # Tinggi tanpa refraksi & koreksi paralaks untuk ARCV Geosentris
    alt_s_noref, _, _ = astro_sun.altaz(pressure_mbar=0.0)
    alt_m_noref, _, _ = astro_moon.altaz(pressure_mbar=0.0)
    hp_moon = math.degrees(math.asin(6378.14 / float(dist_m.km)))
    hp_sun = math.degrees(math.asin(6378.14 / float(dist_s.km)))
    alt_m_geo = float(alt_m_noref.degrees) + hp_moon * math.cos(math.radians(float(alt_m_noref.degrees)))
    alt_s_geo = float(alt_s_noref.degrees) + hp_sun * math.cos(math.radians(float(alt_s_noref.degrees)))
    arcv_geo = alt_m_geo - alt_s_geo

    # Elongasi
    geo_sun = earth.at(t_obj).observe(sun).apparent()
    geo_moon = earth.at(t_obj).observe(moon).apparent()
    elong_geo = float(geo_sun.separation_from(geo_moon).degrees)
    elong_topo = float(astro_sun.separation_from(astro_moon).degrees)

    # Semidiameter, Iluminasi (Fase), dan Lebar Sabit
    sd_moon_arcmin = math.degrees(math.asin(1737.4 / float(dist_m.km))) * 60.0
    sd_sun_arcmin = math.degrees(math.asin(696340.0 / float(dist_s.km))) * 60.0
    iluminasi_persen = 50.0 * (1.0 - math.cos(math.radians(elong_topo)))
    lebar_sabit_arcmin = sd_moon_arcmin * (1.0 - math.cos(math.radians(elong_topo)))

    return {
        "alt_s": float(alt_s.degrees),
        "az_s": float(az_s.degrees),
        "ra_s": float(ra_s.hours),
        "dec_s": float(dec_s.degrees),
        "alt_m": float(alt_m.degrees),
        "az_m": float(az_m.degrees),
        "ra_m": float(ra_m.hours),
        "dec_m": float(dec_m.degrees),
        "rel_alt": float(alt_m.degrees - alt_s.degrees),
        "rel_az": float((az_m.degrees - az_s.degrees + 180.0) % 360.0 - 180.0),
        "arcv_geo": arcv_geo,
        "elong_geo": elong_geo,
        "elong_topo": elong_topo,
        "sd_moon_arcmin": sd_moon_arcmin,
        "sd_sun_arcmin": sd_sun_arcmin,
        "iluminasi_persen": iluminasi_persen,
        "lebar_sabit_arcmin": lebar_sabit_arcmin,
        "dist_moon_km": float(dist_m.km),
    }


def hisab_lengkap_markaz(nama: str, lat: float, lon: float, elev_m: float, tz_jam: float,
                         dt_pilihan: datetime, refraksi: bool = True) -> dict:
    """Menghitung data lengkap ala 4 layar MoonCalc 6.0 untuk satu lokasi."""
    topos = wgs84.latlon(lat, lon, elevation_m=elev_m)
    observer = earth + topos
    tz = timezone(timedelta(hours=tz_jam))
    tekanan = 1010.0 if refraksi else 0.0

    # --- LAYAR 1: WAKTU PILIHAN PENGGUNA ---
    dt_lokal_user = dt_pilihan.replace(tzinfo=tz)
    t_user = ts.from_datetime(dt_lokal_user)
    pos_user = _ukur_posisi_seketika(observer, t_user, tekanan)
    fase_apsis = cari_fase_dan_apsis(t_user)
    t_ijtimak = fase_apsis["ijtimak"]
    umur_user = float((t_user.tt - t_ijtimak.tt) * 24.0) if t_ijtimak is not None else 0.0

    # Terbit & Terbenam Matahari dan Bulan pada tanggal pilihan
    dt_awal = datetime(dt_pilihan.year, dt_pilihan.month, dt_pilihan.day, 0, 0, 0, tzinfo=tz)
    dt_akhir = dt_awal + timedelta(days=1)
    t0, t1 = ts.from_datetime(dt_awal), ts.from_datetime(dt_akhir)

    dip = hitung_dip_derajat(elev_m)
    alt_horizon_deg = -(0.2667 + (0.5667 if refraksi else 0.0) + dip)

    f_sun = almanac.risings_and_settings(eph, sun, topos, horizon_degrees=alt_horizon_deg)
    ts_ev, s_ev = almanac.find_discrete(t0, t1, f_sun)
    sunrises = ekstrak_waktu(ts_ev, s_ev, 1)
    sunsets = ekstrak_waktu(ts_ev, s_ev, 0)
    t_sunrise = sunrises[0] if sunrises else None
    t_ghurub = sunsets[0] if sunsets else None

    f_moon = almanac.risings_and_settings(eph, moon, topos, horizon_degrees=alt_horizon_deg)
    tm_ev, m_ev = almanac.find_discrete(t0, ts.tt_jd(t1.tt + 0.5), f_moon)
    moonrises = [tm for tm in ekstrak_waktu(tm_ev, m_ev, 1) if tm.tt <= t1.tt]
    moonsets = ekstrak_waktu(tm_ev, m_ev, 0)
    t_moonrise = moonrises[0] if moonrises else None

    if t_ghurub is not None:
        ms_after = [tm for tm in moonsets if tm.tt >= t_ghurub.tt]
        t_moonset = ms_after[0] if ms_after else (moonsets[0] if moonsets else None)
    else:
        t_moonset = moonsets[0] if moonsets else None

    lag_menit = float((t_moonset.tt - t_ghurub.tt) * 1440.0) if (t_ghurub is not None and t_moonset is not None) else 0.0

    # --- LAYAR 2: SAAT APPARENT SUNSET (GHURUB) ---
    if t_ghurub is not None:
        pos_ghurub = _ukur_posisi_seketika(observer, t_ghurub, tekanan)
        umur_ghurub = float((t_ghurub.tt - t_ijtimak.tt) * 24.0) if t_ijtimak is not None else 0.0
        kriteria_ghurub = evaluasi_kriteria(
            alt_topo=pos_ghurub["alt_m"],
            arcv_geo=pos_ghurub["arcv_geo"],
            elong_geo=pos_ghurub["elong_geo"],
            lebar_sabit_arcmin=pos_ghurub["lebar_sabit_arcmin"],
            lag_menit=lag_menit,
            umur_jam=umur_ghurub,
        )

        # --- LAYAR 3: MATAHARI -5 DERAJAT & BEST TIME (YALLOP/BRUIN) ---
        jd_scan = np.linspace(t_ghurub.tt, t_ghurub.tt + (90.0 / 1440.0), 181)
        t_scan = ts.tt_jd(jd_scan)
        alt_sun_scan, _, _ = observer.at(t_scan).observe(sun).apparent().altaz(pressure_mbar=0.0)
        idx_min5 = int(np.argmin(np.abs(alt_sun_scan.degrees - (-5.0))))
        t_sun_min5 = t_scan[idx_min5]
        pos_min5 = _ukur_posisi_seketika(observer, t_sun_min5, tekanan)

        offset_best_min = (4.0 / 9.0) * lag_menit if lag_menit > 0 else 20.0
        t_best = ts.tt_jd(t_ghurub.tt + (offset_best_min / 1440.0))
        pos_best = _ukur_posisi_seketika(observer, t_best, tekanan)
    else:
        pos_ghurub = pos_user
        umur_ghurub = umur_user
        kriteria_ghurub = evaluasi_kriteria(0, 0, 0, 0, 0, 0)
        t_sun_min5 = t_user
        pos_min5 = pos_user
        t_best = t_user
        pos_best = pos_user

    fmt_tgl = lambda t_obj: t_obj.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S") if t_obj is not None else "-"
    fmt_jam = lambda t_obj: t_obj.astimezone(tz).strftime("%H:%M:%S") if t_obj is not None else "-"

    return {
        "meta": {
            "Kota": nama,
            "Lintang": lat,
            "Bujur": lon,
            "Elevasi_m": elev_m,
            "Zona_Waktu": f"UTC+{int(tz_jam)}",
            "Refraksi": "ON" if refraksi else "OFF",
            "JD_User": round(float(t_user.ut1), 5),
            "Delta_T_Detik": round(float(t_user.delta_t), 2),
            "Waktu_Pilihan": fmt_tgl(t_user),
            "Sunrise": fmt_jam(t_sunrise),
            "Ghurub": fmt_jam(t_ghurub),
            "Moonrise": fmt_jam(t_moonrise),
            "Moonset": fmt_jam(t_moonset),
            "Lag_Menit": round(lag_menit, 2),
            "Ijtimak": fmt_tgl(t_ijtimak),
            "Purnama": fmt_tgl(fase_apsis["purnama"]),
            "Perigee": f"{fmt_tgl(fase_apsis['perigee'])} ({fase_apsis['perigee_km']:,.0f} km)",
            "Apogee": f"{fmt_tgl(fase_apsis['apogee'])} ({fase_apsis['apogee_km']:,.0f} km)",
        },
        "layar1_user": {**pos_user, "umur_jam": round(umur_user, 2)},
        "layar2_ghurub": {**pos_ghurub, "umur_jam": round(umur_ghurub, 2), **kriteria_ghurub},
        "layar3_min5": {
            "waktu_min5": fmt_jam(t_sun_min5),
            "pos_min5": pos_min5,
            "waktu_best": fmt_jam(t_best),
            "pos_best": pos_best,
        },
    }


def hisab_ghurub(nama: str, lat: float, lon: float, elev_m: float, tz_jam: float,
                 tahun: int, bulan: int, tanggal: int, refraksi: bool = True) -> dict:
    """Ringkasan baris tunggal saat Ghurub untuk pemindaian massal Indonesia."""
    dt_ref = datetime(tahun, bulan, tanggal, 18, 0, 0)
    res = hisab_lengkap_markaz(nama, lat, lon, elev_m, tz_jam, dt_ref, refraksi)
    m = res["meta"]
    g = res["layar2_ghurub"]

    return {
        "Kota": nama,
        "Lintang": lat,
        "Bujur": lon,
        "Elev_m": int(elev_m),
        "Waktu_Ijtimak": m["Ijtimak"],
        "Ghurub": m["Ghurub"],
        "Moonset": m["Moonset"],
        "Lag_Mnt": m["Lag_Menit"],
        "Tinggi_Deg": round(g["alt_m"], 4),
        "Tinggi_DMS": deg_to_dms(g["alt_m"]),
        "Elongasi_Deg": round(g["elong_geo"], 4),
        "Elongasi_DMS": deg_to_dms(g["elong_geo"]),
        "Az_Matahari": deg_to_dms(g["az_s"], is_azimuth=True),
        "Az_Bulan": deg_to_dms(g["az_m"], is_azimuth=True),
        "Umur_Jam": g["umur_jam"],
        "Sabit_Arcmin": round(g["lebar_sabit_arcmin"], 3),
        "Neo_MABIMS": g["Neo_MABIMS"],
        "Wujudul_Hilal": g["Wujudul_Hilal"],
        "Yallop_q": g["Yallop_q"],
        "Yallop": g["Yallop_Status"],
        "Odeh_V": g["Odeh_V"],
    }


def hitung_gerhana_tahunan(tahun: int, tz_jam: float = 7.0) -> list:
    """Mendeteksi daftar Gerhana Matahari & Gerhana Bulan sepanjang tahun (Menu 8 MoonCalc)."""
    tz = timezone(timedelta(hours=tz_jam))
    t0 = ts.utc(tahun, 1, 1)
    t1 = ts.utc(tahun, 12, 31, 23, 59)

    f_conj = almanac.oppositions_conjunctions(eph, moon)
    times, events = almanac.find_discrete(t0, t1, f_conj)

    daftar = []
    for i in range(len(events)):
        ti = times[i]
        ev = int(events[i])
        g_sun = earth.at(ti).observe(sun).apparent()
        g_moon = earth.at(ti).observe(moon).apparent()

        if ev == 1:  # Konjungsi -> Cek Gerhana Matahari
            sep = float(g_sun.separation_from(g_moon).degrees)
            if sep < 1.58:
                jenis = "Gerhana Matahari (Sentral: Total/Cincin)" if sep < 0.98 else "Gerhana Matahari Sebagian"
                daftar.append({
                    "Tanggal_Waktu": ti.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S") + f" (UTC+{int(tz_jam)})",
                    "Jenis_Gerhana": jenis,
                    "Separasi_Geosentris_Deg": round(sep, 4),
                })
        else:  # Oposisi -> Cek Gerhana Bulan
            # Sudut antara pusat Bulan dan pusat bayangan Bumi (-posisi Matahari)
            vec_anti_sun = -g_sun.position.au
            vec_moon = g_moon.position.au
            cos_ang = np.dot(vec_anti_sun, vec_moon) / (np.linalg.norm(vec_anti_sun) * np.linalg.norm(vec_moon))
            sep_umbra = math.degrees(math.acos(np.clip(cos_ang, -1.0, 1.0)))
            if sep_umbra < 1.60:
                if sep_umbra < 0.45:
                    jenis = "Gerhana Bulan Total"
                elif sep_umbra < 1.02:
                    jenis = "Gerhana Bulan Sebagian"
                else:
                    jenis = "Gerhana Bulan Penumbra"
                daftar.append({
                    "Tanggal_Waktu": ti.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S") + f" (UTC+{int(tz_jam)})",
                    "Jenis_Gerhana": jenis,
                    "Separasi_Geosentris_Deg": round(sep_umbra, 4),
                })
    return daftar
