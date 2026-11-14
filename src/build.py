"""Ham HPDmobile dosyalarını 10 saniyelik ortak zaman ızgarasında hizalar.

Neden: etiket (ground truth), ortam sensörü ve ses 10 sn'de bir, görüntü 1 sn'de bir gelir.
Örnek birimi = (ev, 10 sn'lik pencere). Etiketin t anındaki satırı [t, t+10) penceresini temsil eder.
Her hub (sensör kutusu) için aynı satır sırasıyla diziler yazılır; eksik olan yer maske ile işaretlenir.

Çıktı: data/processed/<ev>/
    labels.parquet          ts, occupied, number, cls (0 / 1 / 2+)
    <hub>_env.npy           [T, 5] float32  tvoc, temp, rh, light, co2eq  (eksik = NaN)
    <hub>_img.npy           [T, 32, 32] uint8  pencere ortasına en yakın kare
    <hub>_img.parquet       n_frames, n_dark, offset, zone  (pencere başına)
    <hub>_aud.npy           [T, 800] float16  log1p(ses zarfı)
    <hub>_aud.parquet       aud_ok, aud_len
    stats.json              ham / eşleşen / düşen sayıları (rapor tablosu buradan)

Kullanım:
    python src/build.py H4                 # zip'i diskte olan modaliteleri işler
    python src/build.py H4 --fetch         # büyük zip'leri tek tek indir → işle → sil
    python src/build.py all --fetch
"""
import argparse, io, json, re, sys, zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from download import list_files, RAW  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
INTERIM, OUT = ROOT / "data" / "interim", ROOT / "data" / "processed"
HOMES = [f"H{i}" for i in range(1, 7)]
ENV_COLS = ["tvoc_ppb", "temp_c", "rh_percent", "light_lux", "co2eq_ppm"]
AUD_LEN = 800
TS_RE = re.compile(r"(\d{4}-\d{2}-\d{2})_(\d{6})_(\w+?)_H\d")  # 2019-05-01_000834_RS4_H4


def name_ts(name):
    """Dosya adından (zaman, hub) çıkarır; eşleşmezse None."""
    m = TS_RE.search(name)
    if not m:
        return None
    d, t, hub = m.groups()
    return pd.Timestamp(f"{d} {t[:2]}:{t[2:4]}:{t[4:]}"), hub


def load_stats(home):
    p = OUT / home / "stats.json"
    return json.loads(p.read_text()) if p.exists() else {}


def save_stats(home, key, value):
    s = load_stats(home)
    s[key] = value
    (OUT / home / "stats.json").write_text(json.dumps(s, indent=1, default=int))


def hubs_of(home):
    return sorted(p.name.split("_")[1] for p in (INTERIM / home).glob(f"{home}_*_ENV"))


def build_labels(home):
    fs = sorted((INTERIM / home).glob("*_groundtruth.csv"))
    gt = pd.concat(pd.read_csv(f, parse_dates=["timestamp"]) for f in fs).rename(columns={"timestamp": "ts"})
    raw = len(gt)
    gt = gt.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    gt["cls"] = gt["number"].clip(upper=2).astype("int8")  # 0 / 1 / 2+
    (OUT / home).mkdir(parents=True, exist_ok=True)
    gt.to_parquet(OUT / home / "labels.parquet")
    save_stats(home, "labels", {"days": len(fs), "raw_rows": raw, "rows": len(gt),
                                "cls_counts": gt["cls"].value_counts().sort_index().to_dict()})
    return gt


def grid_index(gt):
    """Zaman → satır numarası. Pencere başına yuvarlanmış zamanı ızgaraya eşler (-1 = ızgara dışı)."""
    idx = pd.Index(gt["ts"])
    return lambda ts: idx.get_indexer(pd.DatetimeIndex(ts).floor("10s"))


def build_env(home, gt):
    for hub in hubs_of(home):
        fs = sorted((INTERIM / home / f"{home}_{hub}_ENV").glob("*.csv"))
        df = pd.concat(pd.read_csv(f, index_col=0, parse_dates=True) for f in fs)
        raw = len(df)
        dup = int(df.index.duplicated().sum())
        df = df[~df.index.duplicated()]
        x = df[ENV_COLS].reindex(gt["ts"]).to_numpy("float32")
        np.save(OUT / home / f"{hub}_env.npy", x)
        matched = int((~np.isnan(x).all(1)).sum())
        # ham CSV zaten 10 sn ızgarasında; ölçüm yoksa satır boş (NaN) gelir
        save_stats(home, f"{hub}/env", {"raw_rows": raw, "duplicates": dup, "matched": matched,
                                        "any_nan": int(np.isnan(x).any(1).sum()), "grid": len(gt)})


def dark_counts(home, hub, row_of, T):
    fs = sorted((INTERIM / home / f"{home}_{hub}_DARKIMAGES").glob("*.csv"))
    if not fs:
        return np.zeros(T, "int16"), 0
    ts = pd.concat(pd.read_csv(f, header=None, names=["ts"], parse_dates=["ts"]) for f in fs)["ts"]
    r = row_of(ts)
    return np.bincount(r[r >= 0], minlength=T).astype("int16"), len(ts)


def sample_hour(gt):
    """Sunumda gösterilecek ham örnek saat: gündüz, kişi sayısının değiştiği ilk saat."""
    ch = gt[(gt["number"].diff() != 0) & gt["ts"].dt.hour.between(8, 19)]
    return (ch["ts"].iloc[1] if len(ch) > 1 else gt["ts"].iloc[0]).floor("h")


def keep_samples(z, home, items, gt):
    """items: (zip içi ad, zaman). Örnek saatteki ham dosyaları data/samples/<ev>/ altına çıkarır."""
    h0 = sample_hour(gt)
    dest = ROOT / "data" / "samples" / home
    for n, t in items:
        if h0 <= t < h0 + pd.Timedelta("1h"):
            z.extract(n, dest)


def build_images(home, hub, zpath, gt):
    T, row_of = len(gt), grid_index(gt)
    with zipfile.ZipFile(zpath) as z:
        names = [n for n in z.namelist() if n.endswith(".png") and "__MACOSX" not in n]
        parsed = [name_ts(n) for n in names]
        keep_samples(z, home, [(names[i], p[0]) for i, p in enumerate(parsed) if p], gt)
        ok = [i for i, p in enumerate(parsed) if p]
        df = pd.DataFrame({"name": [names[i] for i in ok], "ts": [parsed[i][0] for i in ok]})
        df["row"] = row_of(df["ts"])
        df["offset"] = (df["ts"] - df["ts"].dt.floor("10s")).dt.total_seconds().astype(int)
        inside = df[df["row"] >= 0]
        n_frames = np.bincount(inside["row"], minlength=T).astype("int16")
        # pencere ortasına (5. saniye) en yakın kare seçilir
        pick = inside.assign(k=(inside["offset"] - 5).abs()).sort_values(["row", "k"]).drop_duplicates("row")
        img = np.zeros((T, 32, 32), "uint8")
        offset = np.full(T, -1, "int8")
        bad = 0
        for name, r, off in zip(pick["name"], pick["row"], pick["offset"]):
            a = np.asarray(Image.open(io.BytesIO(z.read(name))).convert("L"))
            if a.shape != (32, 32):
                bad += 1
                continue
            img[r], offset[r] = a, off
    np.save(OUT / home / f"{hub}_img.npy", img)
    zone = zone_of_pick(home, hub, pick, T)
    n_dark, dark_raw = dark_counts(home, hub, row_of, T)
    pd.DataFrame({"n_frames": n_frames, "n_dark": n_dark, "offset": offset, "zone": zone}).to_parquet(
        OUT / home / f"{hub}_img.parquet")
    save_stats(home, f"{hub}/img", {"files": len(names), "unparsed": len(names) - len(ok),
                                    "outside_grid": int((df["row"] < 0).sum()), "windows_with_img": int((offset >= 0).sum()),
                                    "bad_shape": bad, "dark_listed": dark_raw, "grid": T})


def zone_of_pick(home, hub, pick, T):
    """Seçilen karenin 'kamerada insan var mı' etiketi (-1 = yok)."""
    fs = sorted((INTERIM / home / f"{home}_{hub}_ZONELABELS").glob("*.csv"))
    zone = np.full(T, -1, "int8")
    if not fs:
        return zone
    zl = pd.concat(pd.read_csv(f, parse_dates=["timestamp"]) for f in fs).drop_duplicates("timestamp")
    m = pick.merge(zl, left_on="ts", right_on="timestamp", how="inner")
    zone[m["row"].to_numpy()] = m["occupied"].to_numpy()
    return zone


def build_audio(home, zpath, gt):
    T, row_of = len(gt), grid_index(gt)
    per_hub = {}
    with zipfile.ZipFile(zpath) as z:
        names = [n for n in z.namelist() if n.endswith(".csv") and "__MACOSX" not in n]
        for n in names:
            p = name_ts(n)
            if p:
                per_hub.setdefault(p[1], []).append((n, p[0]))
        keep_samples(z, home, [it for v in per_hub.values() for it in v], gt)
        for hub in hubs_of(home):
            items = per_hub.get(hub, [])
            aud = np.zeros((T, AUD_LEN), "float16")
            length = np.zeros(T, "int16")
            outside = dup = bad = 0
            rows = row_of([t for _, t in items]) if items else []
            for (n, _), r in zip(items, rows):
                if r < 0:
                    outside += 1
                    continue
                if length[r]:
                    dup += 1
                    continue
                v = np.array(z.read(n).split(), dtype="float64")
                if len(v) == 0 or not np.isfinite(v).all():
                    bad += 1
                    continue
                length[r] = len(v)
                v = v[:AUD_LEN] if len(v) >= AUD_LEN else np.pad(v, (0, AUD_LEN - len(v)))
                aud[r] = np.log1p(np.clip(v, 0, None))  # float16 1e6'yı taşıyamaz → log ölçeği
            np.save(OUT / home / f"{hub}_aud.npy", aud)
            pd.DataFrame({"aud_ok": length > 0, "aud_len": length}).to_parquet(OUT / home / f"{hub}_aud.parquet")
            save_stats(home, f"{hub}/aud", {"files": len(items), "outside_grid": outside, "duplicates": dup,
                                            "bad": bad, "matched": int((length > 0).sum()),
                                            "len_not_800": int(((length > 0) & (length != AUD_LEN)).sum()), "grid": T})


def big_files(home):
    for title, name, size, url, md5 in list_files():
        if home in title.split() and ("Audio" in title or "Image Data" in title):
            out = RAW / (name if "Audio" in title else f"{home}_{title.split()[-1]}_IMAGES.zip")
            yield out, size, url


def run(home, fetch):
    gt = build_labels(home)
    build_env(home, gt)
    targets = list(big_files(home)) if fetch else [(p, None, None) for p in RAW.glob(f"{home}_*.zip")]
    for zpath, size, url in targets:
        is_img = zpath.name.endswith("_IMAGES.zip")  # H4_RS4_IMAGES.zip (H4_DARKIMAGES.zip değil)
        if not (is_img or zpath.name.endswith("_AUDIO.zip")):
            continue
        if fetch and not (zpath.exists() and zpath.stat().st_size == size):
            print(f"  indiriliyor {zpath.name} ({size/1e9:.1f} GB)", flush=True)
            import urllib.request
            urllib.request.urlretrieve(url, zpath.with_suffix(".part"))
            zpath.with_suffix(".part").rename(zpath)
        print(f"  işleniyor {zpath.name}", flush=True)
        if is_img:
            build_images(home, zpath.name.split("_")[1], zpath, gt)
        else:
            build_audio(home, zpath, gt)
        if fetch:
            zpath.unlink()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("home", help="H1..H6 ya da all")
    ap.add_argument("--fetch", action="store_true", help="büyük zip'leri indir, işle, sil")
    a = ap.parse_args()
    for h in HOMES if a.home == "all" else [a.home]:
        print(h, flush=True)
        run(h, a.fetch)
