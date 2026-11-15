import math
from datetime import datetime, timedelta, timezone
from skyfield.api import load, wgs84
from skyfield import almanac

# Muat epemeris JPL DE421
ts = load.timescale()
eph = load('de421.bsp')
earth, sun, moon = eph['earth'], eph['sun'], eph['moon']


def hitung_dip_derajat(elevasi_m: float) -> float:
    """Kerendahan ufuk (dip) dalam derajat berdasarkan elevasi pengamat (meter)."""
    if elevasi_m <= 0:
        return 0.0
    return 1.76 * math.sqrt(elevasi_m) / 60.0


def cari_ijtimak_terdekat(t_ref):
    """Mencari waktu konjungsi geosentris (ijtimak) terdekat dalam rentang ±15 hari."""
    t0 = ts.tt_jd(t_ref.tt - 15)
    t1 = ts.tt_jd(t_ref.tt + 15)
    f = almanac.oppositions_conjunctions(eph, moon)
    times, events = almanac.find_discrete(t0, t1, f)
    konjungsi = [times[i] for i in range(len(events)) if int(events[i]) == 1]
    if len(konjungsi) == 0:
        return None
    return min(konjungsi, key=lambda ti: abs(ti.tt - t_ref.tt))


def evaluasi_kriteria(alt_topo: float, arc_v_geo: float, elong_geo: float,
                      lebar_sabit_arcmin: float, lag_menit: float, umur_jam: float) -> dict:
    """Evaluasi visibilitas hilal: Neo-MABIMS, Yallop (1997), dan Klasik."""
    # 1. Neo-MABIMS (Tinggi Mar'i >= 3.0 deg & Elongasi Geosentris >= 6.4 deg)
    imkan_mabims = (alt_topo >= 3.0) and (elong_geo >= 6.4)

    # 2. Yallop (1997) - Parameter q
    w = lebar_sabit_arcmin
    arcv_min = 11.8371 - 6.3226 * w + 0.7319 * (w ** 2) - 0.1018 * (w ** 3)
    q = (arc_v_geo - arcv_min) / 10.0

    if q > 0.216:
        kat_yallop = "A (Mudah terlihat mata telanjang)"
    elif q > -0.014:
        kat_yallop = "B (Terlihat pada kondisi atmosfer sangat cerah)"
    elif q > -0.160:
        kat_yallop = "C (Memerlukan alat bantu optik terlebih dahulu)"
    elif q > -0.232:
        kat_yallop = "D (Hanya terlihat dengan teleskop)"
    elif q > -0.293:
        kat_yallop = "E (Tidak terlihat dengan teleskop konvensional)"
    else:
        kat_yallop = "F (Di bawah limit Danjon / Mustahil)"

    # 3. Babylonian Klasik (Umur > 24 jam & Lag > 48 menit)
    babylonian = (umur_jam > 24.0) and (lag_menit > 48.0)

    return {
        "Neo_MABIMS": "IMKAN RUKYAT" if imkan_mabims else "BELUM IMKAN",
        "Yallop_q": round(float(q), 3),
        "Yallop_Status": kat_yallop,
        "Babylonian": "Terlihat" if babylonian else "Tidak Terlihat"
    }


def hisab_ghurub(nama: str, lat: float, lon: float, elev_m: float, tz_jam: float,
                 tahun: int, bulan: int, tanggal: int, refraksi: bool = True) -> dict:
    """Menghitung seluruh parameter hilal tepat pada saat Apparent Sunset (Ghurub)."""
    topos = wgs84.latlon(lat, lon, elevation_m=elev_m)
    observer = earth + topos

    # Rentang pencarian sunset & moonset dalam hari lokal
    tz = timezone(timedelta(hours=tz_jam))
    dt_awal = datetime(tahun, bulan, tanggal, 12, 0, 0, tzinfo=tz)
    dt_akhir = datetime(tahun, bulan, tanggal, 22, 0, 0, tzinfo=tz)
    t0 = ts.from_datetime(dt_awal)
    t1 = ts.from_datetime(dt_akhir)

    # Tinggi piringan atas Matahari saat ghurub: -(semidiameter ~0.2667 + refraksi 0.5667 + dip)
    dip = hitung_dip_derajat(elev_m)
    alt_sunset_deg = -(0.2667 + (0.5667 if refraksi else 0.0) + dip)

    f_sun = almanac.risings_and_settings(eph, sun, topos, horizon_degrees=alt_sunset_deg)
    t_events, events = almanac.find_discrete(t0, t1, f_sun)
    sunsets = [t_events[i] for i in range(len(events)) if int(events[i]) == 0]
    if len(sunsets) == 0:
        return {"Kota": nama, "Error": "Ghurub tidak ditemukan"}
    t_ghurub = sunsets[0]

    # Waktu Moonset terdekat setelah ghurub
    f_moon = almanac.risings_and_settings(eph, moon, topos, horizon_degrees=alt_sunset_deg)
    tm_events, m_events = almanac.find_discrete(t0, ts.tt_jd(t1.tt + 0.25), f_moon)
    moonsets = [tm_events[i] for i in range(len(m_events)) if int(m_events[i]) == 0]
    t_moonset = moonsets[0] if len(moonsets) > 0 else None
    lag_menit = float((t_moonset.tt - t_ghurub.tt) * 1440.0) if t_moonset is not None else 0.0

    # Posisi Toposentris saat Ghurub
    tekanan = 1010.0 if refraksi else 0.0
    astro_sun = observer.at(t_ghurub).observe(sun).apparent()
    astro_moon = observer.at(t_ghurub).observe(moon).apparent()

    alt_s, az_s, _ = astro_sun.altaz(temperature_C=27.0, pressure_mbar=tekanan)
    alt_m, az_m, dist_m = astro_moon.altaz(temperature_C=27.0, pressure_mbar=tekanan)

    # Posisi Geosentris (untuk Elongasi MABIMS & ARCV Yallop)
    geo_sun = earth.at(t_ghurub).observe(sun).apparent()
    geo_moon = earth.at(t_ghurub).observe(moon).apparent()
    elong_geo = float(geo_sun.separation_from(geo_moon).degrees)
    elong_topo = float(astro_sun.separation_from(astro_moon).degrees)

    # Semidiameter & Lebar Sabit (arcmin)
    sd_moon_deg = math.degrees(math.asin(1737.4 / float(dist_m.km)))
    sd_moon_arcmin = sd_moon_deg * 60.0
    lebar_sabit_arcmin = sd_moon_arcmin * (1.0 - math.cos(math.radians(elong_topo)))

    # Umur Bulan dari Ijtimak terdekat
    t_ijtimak = cari_ijtimak_terdekat(t_ghurub)
    umur_jam = float((t_ghurub.tt - t_ijtimak.tt) * 24.0) if t_ijtimak is not None else 0.0

    # ARCV geosentris pendekatan untuk Yallop
    alt_s_geo, _, _ = geo_sun.altaz()
    alt_m_geo, _, _ = geo_moon.altaz()
    arcv_geo = float(alt_m_geo.degrees - alt_s_geo.degrees)

    kriteria = evaluasi_kriteria(
        alt_topo=float(alt_m.degrees),
        arc_v_geo=arcv_geo,
        elong_geo=elong_geo,
        lebar_sabit_arcmin=lebar_sabit_arcmin,
        lag_menit=lag_menit,
        umur_jam=umur_jam
    )

    dt_ghurub_lokal = t_ghurub.astimezone(tz)
    dt_moonset_lokal = t_moonset.astimezone(tz) if t_moonset is not None else None
    dt_ijtimak_lokal = t_ijtimak.astimezone(tz) if t_ijtimak is not None else None

    return {
        "Kota": nama,
        "Lintang": lat,
        "Bujur": lon,
        "Elevasi_m": elev_m,
        "Waktu_Ijtimak": dt_ijtimak_lokal.strftime("%Y-%m-%d %H:%M:%S") if dt_ijtimak_lokal is not None else "-",
        "Ghurub": dt_ghurub_lokal.strftime("%H:%M:%S"),
        "Moonset": dt_moonset_lokal.strftime("%H:%M:%S") if dt_moonset_lokal is not None else "-",
        "Lag_Menit": round(lag_menit, 2),
        "Tinggi_Hilal_Deg": round(float(alt_m.degrees), 4),
        "Elongasi_Geo_Deg": round(elong_geo, 4),
        "Azimut_Matahari": round(float(az_s.degrees), 2),
        "Azimut_Bulan": round(float(az_m.degrees), 2),
        "Umur_Bulan_Jam": round(umur_jam, 2),
        "Lebar_Sabit_Arcmin": round(lebar_sabit_arcmin, 3),
        **kriteria
    }
