"""Keşifsel veri analizi (EDA) grafikleri → reports/figures/*.png

Her fonksiyon bir şekil üretir ve rapora girecek sayıları döndürür (reports/eda_numbers.json).
Kullanım: python src/eda.py            # hepsi
          python src/eda.py fig02      # tek şekil
"""
import json, sys
from functools import lru_cache
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from build import ENV_COLS, HOMES, OUT, ROOT, hubs_of  # noqa: E402
from clean import clean_env  # noqa: E402

FIG = ROOT / "reports" / "figures"
NUMS = ROOT / "reports" / "eda_numbers.json"
# sınıf renkleri: dataviz referans paletinin ilk üç kategorik yuvası (renk körlüğü testli)
CLS_COLOR = {0: "#2a78d6", 1: "#eb6834", 2: "#1baf7a"}
CLS_NAME = {0: "0 kişi (boş)", 1: "1 kişi", 2: "2+ kişi"}
ENV_TR = {"tvoc_ppb": "TVOC (ppb)", "temp_c": "Sıcaklık (°C)", "rh_percent": "Bağıl nem (%)",
          "light_lux": "Işık (lux)", "co2eq_ppm": "eCO2 (ppm)"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
LIGHT = "#b5b4ad"
ACCENT = "#6250d6"  # sınıf dışı vurgu (sınıf renkleri yalnız sınıflar için)

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 200, "savefig.bbox": "tight", "font.size": 9,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "axes.titlesize": 10, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.axisbelow": True, "xtick.color": MUTED, "ytick.color": MUTED,
    "legend.frameon": False,
})


def labels(h):
    return pd.read_parquet(OUT / h / "labels.parquet")


def env(h, hub, clean=True):
    x = np.load(OUT / h / f"{hub}_env.npy")
    return clean_env(x, hub, ENV_COLS) if clean else x


def save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.png")
    plt.close(fig)


def fig01_class_distribution():
    """Sınıf sayıları: toplamda yönerge koşulu (≥3 sınıf, ≥150/sınıf) + ev bazında dengesizlik."""
    gts = {h: labels(h) for h in HOMES}
    tot = pd.concat(gts.values())["cls"].value_counts().sort_index()
    per = pd.DataFrame({h: g["cls"].value_counts().reindex([0, 1, 2], fill_value=0) for h, g in gts.items()}).T
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.6), gridspec_kw={"width_ratios": [1, 2]})
    a.bar([CLS_NAME[c] for c in tot.index], tot.values, color=[CLS_COLOR[c] for c in tot.index], width=0.6)
    for i, v in enumerate(tot.values):
        a.text(i, v, f"{v:,}".replace(",", "."), ha="center", va="bottom", color=INK)
    a.set_title("Toplam örnek (10 sn pencere)")
    a.set_ylabel("Pencere sayısı")
    pct = per.div(per.sum(1), axis=0) * 100
    left = np.zeros(len(pct))
    for c in [0, 1, 2]:
        b.barh(pct.index, pct[c], left=left, color=CLS_COLOR[c], label=CLS_NAME[c], height=0.6,
               edgecolor="white", linewidth=1.5)
        for y, (l, v) in enumerate(zip(left, pct[c])):
            if v > 6:
                b.text(l + v / 2, y, f"%{v:.0f}", ha="center", va="center", color="white", fontsize=8)
        left += pct[c]
    b.invert_yaxis()
    b.set_xlim(0, 100)
    b.set_xlabel("Ev içindeki pay (%)")
    b.set_title("Ev bazında sınıf payları")
    b.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.18))
    b.grid(axis="y", visible=False)
    save(fig, "fig01_sinif_dagilimi")
    return {"total": tot.to_dict(), "per_home": per.to_dict("index")}


def fig02_hour_of_day():
    """Saat × sınıf payı: 2+ sınıfı geceye yığılıyor → günün saati ile sınıf karışık (confound)."""
    fig, axes = plt.subplots(2, 3, figsize=(10, 5), sharex=True, sharey=True)
    out = {}
    for ax, h in zip(axes.flat, HOMES):
        g = labels(h)
        p = pd.crosstab(g["ts"].dt.hour, g["cls"], normalize="index").reindex(columns=[0, 1, 2], fill_value=0)
        ax.stackplot(p.index, *[p[c] * 100 for c in [0, 1, 2]], colors=[CLS_COLOR[c] for c in [0, 1, 2]],
                     edgecolor="white", linewidth=0.8)
        ax.set_title(h)
        ax.set_xlim(0, 23)
        ax.set_xticks([0, 6, 12, 18, 23])
        ax.grid(False)
        out[h] = {"2+_gece_00_05": round(p.loc[0:5, 2].mean() * 100, 1), "2+_ogle_11_16": round(p.loc[11:16, 2].mean() * 100, 1),
                  "bos_ogle_11_16": round(p.loc[11:16, 0].mean() * 100, 1)}
    for ax in axes[1]:
        ax.set_xlabel("Saat")
    for ax in axes[:, 0]:
        ax.set_ylabel("Pay (%)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=CLS_COLOR[c]) for c in [0, 1, 2]]
    fig.legend(handles, CLS_NAME.values(), ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.04))
    fig.suptitle("Günün saatine göre sınıf payları", fontweight="bold")
    save(fig, "fig02_saat_sinif")
    return out


def fig03_segment_lengths():
    """Etiket kaç dakika sabit kalıyor: komşu pencereler neredeyse aynı → rastgele bölme sızıntı yapar."""
    runs = []
    for h in HOMES:
        g = labels(h)
        seg = (g["cls"] != g["cls"].shift()).cumsum().rename("seg")
        r = g.groupby(seg).agg(cls=("cls", "first"), n=("cls", "size"))
        r["home"] = h
        runs.append(r)
    runs = pd.concat(runs)
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    for c in [0, 1, 2]:
        m = np.sort(runs.loc[runs["cls"] == c, "n"].to_numpy() * 10 / 60)
        ax.step(m, np.arange(1, len(m) + 1) / len(m), where="post", color=CLS_COLOR[c], lw=2, label=CLS_NAME[c])
    ax.set_xscale("log")
    ax.set_xlabel("Kesintisiz aynı sınıf süresi (dakika, log)")
    ax.set_ylabel("Birikimli oran")
    ax.set_title("Etiket segment süreleri (ECDF)")
    ax.legend()
    total = sum(len(labels(h)) for h in HOMES)
    same_next = 1 - (len(runs) - len(HOMES)) / total
    save(fig, "fig03_segment_sureleri")
    return {"segments": len(runs), "median_min": (runs.groupby("cls")["n"].median() * 10 / 60).round(1).to_dict(),
            "p_same_next_window": round(same_next, 5)}


def env_frame():
    """Tüm ev×hub ortam verisi, hub içinde z-skoru (hub'lar arası mutlak fark sınıfı maskelemesin)."""
    parts = []
    for h in HOMES:
        cls = labels(h)["cls"].to_numpy()
        for hub in hubs_of(h):
            x = env(h, hub)
            z = (x - np.nanmean(x, 0)) / (np.nanstd(x, 0) + 1e-9)
            df = pd.DataFrame(z, columns=ENV_COLS)
            df["cls"], df["home"], df["hub"] = cls, h, hub
            parts.append(df)
    return pd.concat(parts, ignore_index=True)


def fig04_env_by_class():
    """Ortam özelliklerinin sınıfa göre dağılımı (hub içi z-skoru) + ayırt edicilik özeti."""
    df = env_frame()
    fig, axes = plt.subplots(1, 5, figsize=(11, 3.4), sharey=True)
    out = {}
    for ax, c in zip(axes, ENV_COLS):
        data = [df.loc[df["cls"] == k, c].dropna().to_numpy() for k in [0, 1, 2]]
        bp = ax.boxplot(data, widths=0.55, showfliers=False, patch_artist=True,
                        medianprops={"color": "white", "lw": 1.5}, whiskerprops={"color": MUTED},
                        capprops={"color": MUTED})
        for patch, k in zip(bp["boxes"], [0, 1, 2]):
            patch.set(facecolor=CLS_COLOR[k], edgecolor=CLS_COLOR[k])
        ax.set_xticks([1, 2, 3], ["0", "1", "2+"])
        ax.set_title(ENV_TR[c])
        ax.set_xlabel("Kişi")
        out[c] = {CLS_NAME[k]: dict(zip(["q1", "median", "q3"], np.round(np.nanpercentile(d, [25, 50, 75]), 2)))
                  for k, d in zip([0, 1, 2], data)}
    axes[0].set_ylabel("Hub içi z-skoru")
    axes[0].set_ylim(-3, 3)
    fig.suptitle("Ortam sensörleri sınıfa göre (aykırı noktalar gizli)", fontweight="bold", y=1.03)
    save(fig, "fig04_ortam_sinif")
    return out


def fig05_rh_cleaning():
    """Öncesi/sonrası: imkânsız nem değerleri (~3285 %) ve takılı RS5 nem sensörü."""
    raw = np.concatenate([env(h, hub, clean=False)[:, 2] for h in HOMES for hub in hubs_of(h)])
    raw = raw[~np.isnan(raw)]
    fig, (a, b, c) = plt.subplots(1, 3, figsize=(12, 3.6), gridspec_kw={"wspace": 0.3})
    a.hist(raw, bins=120, color=MUTED, log=True)
    a.set_title("Önce: ham nem (log ölçek)")
    a.set_xlabel("Bağıl nem (%)")
    a.set_ylabel("Okuma sayısı")
    bad = raw > 100
    a.annotate(f"{bad.sum()} okuma ≈3285 %\n(fiziksel olarak imkânsız)", xy=(3285, 5), xytext=(1500, 2e4),
               arrowprops={"arrowstyle": "->", "color": INK}, color=INK)
    ok = np.concatenate([env(h, hub)[:, 2] for h in HOMES for hub in hubs_of(h)])  # clean_env uygulanmış
    ok = ok[~np.isnan(ok)]
    b.hist(ok, bins=100, color=MUTED)
    b.set_title("Sonra: temizlenmiş nem")
    b.set_xlabel("Bağıl nem (%)")
    h = "H3"
    t = labels(h)["ts"]
    sl = slice(0, 8640 * 3)  # ilk 3 gün
    for hub in hubs_of(h):
        y = env(h, hub, clean=False)[sl, 2]
        y = np.where(y > 100, np.nan, y)
        c.plot(t[sl], y, lw=1.6 if hub == "RS5" else 0.8, color=ACCENT if hub == "RS5" else LIGHT,
               label="RS5 (takılı)" if hub == "RS5" else None)
    c.set_title(f"{h}: RS5 nemi takılı (düz çizgi)")
    c.set_ylabel("Bağıl nem (%)")
    c.legend(loc="upper right")
    c.tick_params(axis="x", rotation=30)
    save(fig, "fig05_nem_temizleme")
    return {"rh_over_100": int(bad.sum()), "rh_total": int(len(raw)),
            "rs5_std": {h: round(float(np.nanstd(env(h, "RS5", clean=False)[:, 2].clip(0, 100))), 2)
                        for h in HOMES if "RS5" in hubs_of(h)}}


def fig06_gas_floor():
    """eCO2 ve TVOC sensörü zamanın çoğunda taban değerde → bilgi taşıma kapasitesi düşük."""
    rows = []
    for h in HOMES:
        for hub in hubs_of(h):
            x = env(h, hub, clean=False)
            v = ~np.isnan(x[:, 4])
            rows.append({"etiket": f"{h}-{hub}", "eCO2 = 400 ppm": (x[v, 4] == 400).mean() * 100,
                         "TVOC = 0 ppb": (x[v, 0] == 0).mean() * 100})
    df = pd.DataFrame(rows).set_index("etiket")
    fig, ax = plt.subplots(figsize=(11, 3.4))
    xs = np.arange(len(df))
    ax.bar(xs - 0.2, df["eCO2 = 400 ppm"], 0.38, color=MUTED, label="eCO2 = 400 ppm (sensör tabanı)")
    ax.bar(xs + 0.2, df["TVOC = 0 ppb"], 0.38, color=LIGHT, label="TVOC = 0 ppb")
    ax.set_xticks(xs, df.index, rotation=60, ha="right")
    ax.set_ylabel("Zamanın payı (%)")
    ax.set_ylim(0, 100)
    ax.legend(ncol=2, loc="lower center", bbox_to_anchor=(0.5, 1.0))
    ax.set_title("Gaz sensörleri çoğu zaman taban değerde", pad=34)
    ax.grid(axis="x", visible=False)
    save(fig, "fig06_gaz_taban")
    return df.round(1).to_dict("index")


# --- görüntü / ses yardımcıları ------------------------------------------------------------------
def img_meta(h, hub):
    return pd.read_parquet(OUT / h / f"{hub}_img.parquet")


def aud_ok(h, hub):
    return pd.read_parquet(OUT / h / f"{hub}_aud.parquet")["aud_ok"].to_numpy()


def imgs(h, hub):
    """[T, 32, 32] kareler; mmap = dosya belleğe tümüyle yüklenmez, gerekeni diskten okur."""
    return np.load(OUT / h / f"{hub}_img.npy", mmap_mode="r")


@lru_cache(None)
def brightness(h, hub):
    """Pencere başına seçilen karenin ortalama pikseli (0–255); karesi olmayan pencere NaN."""
    m = img_meta(h, hub)["offset"].to_numpy() >= 0
    b = np.full(len(m), np.nan, "float32")
    b[m] = imgs(h, hub)[m].reshape(m.sum(), -1).mean(1)
    return b


@lru_cache(None)
def aud_energy(h, hub):
    """Pencere başına ses enerjisi = log1p(ses zarfı) ortalaması; ses yoksa NaN. Parça parça okunur (bellek)."""
    x = np.load(OUT / h / f"{hub}_aud.npy", mmap_mode="r")
    e = np.empty(len(x), "float32")
    for i in range(0, len(x), 50_000):
        e[i:i + 50_000] = x[i:i + 50_000].astype("float32").mean(1)
    e[~aud_ok(h, hub)] = np.nan
    return e


def hub_z(v):
    """Hub içi z-skoru: her kutunun kendi ortalaması 0, std 1 → kutular arası kalibrasyon farkı silinir."""
    return (v - np.nanmean(v)) / (np.nanstd(v) + 1e-9)


def pairs():
    return [(h, hub) for h in HOMES for hub in hubs_of(h)]


def pct(a, b):
    return f"{100 * a / b:.1f}"


def tab01_data_summary():
    """Veri özeti tablosu (Kriter 2–4): ham dosya → ızgaraya eşleşen → düşen. stats.json'dan, elle sayı yok."""
    L = ["# Veri özeti", "", "`python src/eda.py tab01` ile `data/processed/*/stats.json`'dan üretilir; elle düzenleme.", "",
         "## Ev bazında", "", "| Ev | Gün | Pencere (10 sn) | Hub | 0 kişi | 1 kişi | 2+ kişi |", "|---|---|---|---|---|---|---|"]
    tot = {"win": 0, "c": [0, 0, 0], "img": 0, "img_out": 0, "dark": 0, "aud": 0, "aud_m": 0, "aud_out": 0}
    S = {h: json.loads((OUT / h / "stats.json").read_text()) for h in HOMES}
    for h in HOMES:
        lab = S[h]["labels"]
        c = [lab["cls_counts"].get(str(k), 0) for k in range(3)]
        L.append(f"| {h} | {lab['days']} | {lab['rows']:,} | {len(hubs_of(h))} | " + " | ".join(f"{v:,}" for v in c) + " |")
        tot["win"] += lab["rows"]
        tot["c"] = [a + b for a, b in zip(tot["c"], c)]
    L.append(f"| **Toplam** | | **{tot['win']:,}** | | " + " | ".join(f"**{v:,}**" for v in tot["c"]) + " |")
    L += ["", "## Ev × hub × modalite", "",
          "Oranlar ızgaradaki pencere sayısına göre. *Ortam boş satır* = en az bir sensör değeri NaN. "
          "*Izgara dışı* = etiket aralığının dışında kalan (düşen) dosya. *Karanlık* = yazarların zip'ten çıkardığı kare (H2 için liste yayınlanmamış → 0).", "",
          "| Ev | Hub | Ortam eşleşen % | Ortam boş satır % | Kare dosyası | Izgara dışı | Karesi olan pencere % | Karanlık kare | "
          "Ses dosyası | Ses eşleşen % | Ses ızgara dışı | Bozuk ses |", "|" + "---|" * 12]
    for h, hub in pairs():
        s, T = S[h], S[h]["labels"]["rows"]
        e, i, a = s.get(f"{hub}/env", {}), s.get(f"{hub}/img", {}), s.get(f"{hub}/aud", {})
        L.append(f"| {h} | {hub} | {pct(e.get('matched', 0), T)} | {pct(e.get('any_nan', 0), T)} | {i.get('files', 0):,} | "
                 f"{i.get('outside_grid', 0):,} | {pct(i.get('windows_with_img', 0), T)} | {i.get('dark_listed', 0):,} | "
                 f"{a.get('files', 0):,} | {pct(a.get('matched', 0), T)} | {a.get('outside_grid', 0):,} | {a.get('bad', 0)} |")
        tot["img"] += i.get("files", 0); tot["img_out"] += i.get("outside_grid", 0); tot["dark"] += i.get("dark_listed", 0)
        tot["aud"] += a.get("files", 0); tot["aud_m"] += a.get("matched", 0); tot["aud_out"] += a.get("outside_grid", 0)
    L += ["", f"**Toplam:** {tot['img']:,} kare dosyası ({tot['img_out']:,} ızgara dışı), {tot['dark']:,} karanlık kare "
          f"(listede, görüntüsü yok), {tot['aud']:,} ses dosyası ({tot['aud_m']:,} eşleşti, {tot['aud_out']:,} ızgara dışı).", ""]
    out = ROOT / "reports" / "veri_ozeti.md"
    out.write_text("\n".join(L))
    return tot


def fig07_completeness():
    """Eksik modalite haritası: ev×hub için her modalitenin bulunduğu pencere payı."""
    cols = ["Ortam (tam satır)", "Kare (aydınlık)", "Yalnız karanlık", "Kare yok", "Ses", "Üçü birden"]
    rows, idx = [], []
    for h, hub in pairs():
        e = ~np.isnan(env(h, hub, clean=False)).any(1)
        m = img_meta(h, hub)
        im = m["offset"].to_numpy() >= 0
        dk = ~im & (m["n_dark"].to_numpy() > 0)
        a = aud_ok(h, hub)
        rows.append([e.mean(), im.mean(), dk.mean(), (~im & ~dk).mean(), a.mean(), (e & im & a).mean()])
        idx.append(f"{h}-{hub}")
    df = pd.DataFrame(np.array(rows) * 100, index=idx, columns=cols)
    fig, ax = plt.subplots(figsize=(7, 9))
    ax.imshow(df.to_numpy(), cmap="Purples", vmin=0, vmax=100, aspect="auto")
    for (r, c), v in np.ndenumerate(df.to_numpy()):
        ax.text(c, r, f"{v:.0f}", ha="center", va="center", fontsize=7, color="white" if v > 60 else INK)
    ax.set_xticks(range(len(cols)), cols, rotation=30, ha="right")
    ax.set_yticks(range(len(idx)), idx, fontsize=7)
    ax.grid(False)
    ax.set_title("Pencerelerin yüzde kaçında hangi modalite var")
    save(fig, "fig07_eksik_modalite")
    return {"mean": df.mean().round(1).to_dict(), "all3_min": df["Üçü birden"].idxmin(),
            "all3_min_pct": round(df["Üçü birden"].min(), 1)}


def fig08_example_frames():
    """Her sınıftan rastgele kareler: 32×32 gri görüntüde insan ancak kaba bir leke olarak görünüyor."""
    rng = np.random.default_rng(0)
    n = 8
    fig, axes = plt.subplots(3, n, figsize=(n * 1.2, 4.4))
    for r, k in enumerate([0, 1, 2]):
        picks = []
        while len(picks) < n:
            h, hub = pairs()[rng.integers(len(pairs()))]
            g = labels(h)
            ok = np.flatnonzero((img_meta(h, hub)["offset"].to_numpy() >= 0) & (g["cls"].to_numpy() == k))
            if len(ok):
                i = rng.choice(ok)
                picks.append((h, hub, i, g["ts"].iloc[i]))
        for c, (h, hub, i, t) in enumerate(picks):
            ax = axes[r, c]
            ax.imshow(imgs(h, hub)[i], cmap="gray", vmin=0, vmax=255)
            ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
            ax.set_xlabel(f"{h}-{hub}\n{t:%H:%M}", fontsize=6, color=MUTED)
            for sp in ax.spines.values():
                sp.set_visible(True); sp.set_color(CLS_COLOR[k]); sp.set_linewidth(2)
        axes[r, 0].set_ylabel(CLS_NAME[k], color=INK, fontsize=8)
    fig.suptitle("Sınıflara göre örnek kareler (32×32, gri)", fontweight="bold")
    save(fig, "fig08_ornek_kareler")
    return {}


def fig09_brightness_light():
    """Modaliteler arası: kamera parlaklığı ↔ ışık sensörü. Uyum = iki modalite aynı anı gösteriyor (hizalama doğru)."""
    xs, ys, rho, dark = [], [], {}, []
    for h, hub in pairs():
        lux = env(h, hub)[:, 3]
        b = brightness(h, hub)
        dk = (img_meta(h, hub)["offset"].to_numpy() < 0) & (img_meta(h, hub)["n_dark"].to_numpy() > 0)
        v = ~np.isnan(lux) & ~np.isnan(b)
        rho[f"{h}-{hub}"] = round(pd.Series(lux[v]).corr(pd.Series(b[v]), method="spearman"), 2)
        xs.append(lux[v]); ys.append(b[v])
        w = ~np.isnan(lux)
        dark.append(pd.DataFrame({"lux": lux[w], "dark": dk[w]}))
    x, y = np.concatenate(xs), np.concatenate(ys)
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.8), gridspec_kw={"wspace": 0.3})
    hb = a.hexbin(np.log10(x + 1), y, gridsize=60, cmap="Purples", bins="log", mincnt=1)
    fig.colorbar(hb, ax=a, label="Pencere sayısı (log)")
    a.set_xlabel("Işık sensörü, log10(lux + 1)")
    a.set_ylabel("Karenin ortalama parlaklığı (0–255)")
    a.set_title(f"Kamera ↔ ışık sensörü (Spearman ρ medyan {np.median(list(rho.values())):.2f})")
    d = pd.concat(dark)
    bins = [0, 1, 3, 10, 30, 100, 300, 1000, 1e6]
    d["bin"] = pd.cut(d["lux"], bins, right=False)
    r = d.groupby("bin", observed=True)["dark"].mean() * 100
    b.bar(range(len(r)), r.values, color=MUTED, width=0.6)
    b.set_xticks(range(len(r)), ["0", "1–3", "3–10", "10–30", "30–100", "100–300", "300–1k", "1k+"][:len(r)],
                 rotation=35, ha="right")
    b.set_xlabel("Işık sensörü (lux)")
    b.set_ylabel("Karesi karanlık diye atılmış pencere (%)")
    b.set_title("Karanlık kareler düşük ışıkta")
    b.grid(axis="x", visible=False)
    save(fig, "fig09_parlaklik_isik")
    return {"spearman": rho, "dark_pct_by_lux": {str(k): round(v, 1) for k, v in r.items()}}


def fig10_audio_by_class():
    """Ses modalitesi: sınıf başına örnek zarflar + hub içi z-skorlu enerji dağılımı."""
    fig = plt.figure(figsize=(11, 4))
    gs = fig.add_gridspec(3, 2, width_ratios=[1.6, 1], wspace=0.25, hspace=0.15)
    b = fig.add_subplot(gs[:, 1])
    h, hub = "H1", "RS2"
    g, e = labels(h), aud_energy(h, hub)
    x = np.load(OUT / h / f"{hub}_aud.npy", mmap_mode="r")
    for k in [0, 1, 2]:
        a = fig.add_subplot(gs[k, 0])
        ok = np.flatnonzero((g["cls"].to_numpy() == k) & ~np.isnan(e))
        i = ok[np.argsort(e[ok])[len(ok) // 2]]  # sınıfın medyan enerjili penceresi = tipik örnek
        a.plot(np.arange(800) / 80, x[i].astype("float32"), color=CLS_COLOR[k], lw=0.7)
        a.set_ylim(6, 17)
        a.set_ylabel(CLS_NAME[k], fontsize=7)
        a.grid(axis="x", visible=False)
        if k == 0:
            a.set_title(f"{h}-{hub}: sınıf başına tipik ses zarfı, log1p", loc="left")
        if k < 2:
            a.tick_params(labelbottom=False)
    a.set_xlabel("Pencere içi zaman (sn)")
    z, c = [], []
    for hh, hb in pairs():
        v = hub_z(aud_energy(hh, hb))
        z.append(v); c.append(labels(hh)["cls"].to_numpy())
    z, c = np.concatenate(z), np.concatenate(c)
    data = [z[(c == k) & ~np.isnan(z)] for k in [0, 1, 2]]
    bp = b.boxplot(data, widths=0.55, showfliers=False, patch_artist=True, medianprops={"color": "white", "lw": 1.5},
                   whiskerprops={"color": MUTED}, capprops={"color": MUTED})
    for patch, k in zip(bp["boxes"], [0, 1, 2]):
        patch.set(facecolor=CLS_COLOR[k], edgecolor=CLS_COLOR[k])
    b.set_xticks([1, 2, 3], ["0", "1", "2+"])
    b.set_xlabel("Kişi")
    b.set_ylabel("Ses enerjisi (hub içi z-skoru)")
    b.set_title("Tüm evler: ses enerjisi sınıfa göre")
    save(fig, "fig10_ses_sinif")
    return {CLS_NAME[k]: dict(zip(["q1", "median", "q3"], np.round(np.percentile(d, [25, 50, 75]), 2)))
            for k, d in zip([0, 1, 2], data)}


def fig11_day_timeline():
    """Modaliteler arası: aynı gün, aynı hub; etiket, ışık, kamera, ses ve kamera-insan etiketi alt alta."""
    h, hub = "H1", "RS2"
    g = labels(h)
    day = g["ts"].dt.date
    # 2+ dahil üç sınıfın da görüldüğü, en çok sınıf değişen gün
    ch = g.assign(d=day, sw=g["cls"].diff().ne(0)).groupby("d").agg(sw=("sw", "sum"), k=("cls", "nunique"))
    d0 = ch[ch["k"] == 3]["sw"].idxmax()
    m = (day == d0).to_numpy()
    t = g["ts"][m]
    meta = img_meta(h, hub)[m]
    fig, ax = plt.subplots(5, 1, figsize=(11, 7), sharex=True, gridspec_kw={"height_ratios": [0.5, 1, 1, 1, 0.5]})
    cls = g["cls"][m].to_numpy()
    for k in [0, 1, 2]:
        ax[0].fill_between(t, 0, 1, where=cls == k, color=CLS_COLOR[k], step="post", lw=0, label=CLS_NAME[k])
    ax[0].set_yticks([]); ax[0].set_title(f"{h}-{hub}, {d0}: aynı gün beş kanal", loc="left")
    ax[0].legend(ncol=3, loc="lower right", bbox_to_anchor=(1, 1.0), fontsize=7)
    ax[1].plot(t, env(h, hub)[m, 3], color=MUTED, lw=0.8); ax[1].set_ylabel("Işık (lux)")
    ax[2].plot(t, brightness(h, hub)[m], color=MUTED, lw=0.6)
    dk = (meta["offset"].to_numpy() < 0) & (meta["n_dark"].to_numpy() > 0)
    ax[2].fill_between(t, 0, 255, where=dk, color=LIGHT, alpha=0.5, step="post", lw=0, label="karanlık (kare yok)")
    ax[2].set_ylabel("Kare parlaklığı"); ax[2].legend(loc="upper right", fontsize=7)
    ax[3].plot(t, pd.Series(aud_energy(h, hub)[m]).rolling(6, min_periods=1).median(), color=MUTED, lw=0.7)
    ax[3].set_ylabel("Ses enerjisi\n(1 dk medyan)")
    zn = meta["zone"].to_numpy()
    ax[4].fill_between(t, 0, 1, where=zn == 1, color=ACCENT, step="post", lw=0, label="kamerada insan")
    ax[4].fill_between(t, 0, 1, where=zn == -1, color=GRID, step="post", lw=0, label="etiket yok")
    ax[4].set_yticks([]); ax[4].legend(ncol=2, loc="upper right", fontsize=7)
    ax[4].xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%H:%M"))
    for a_ in ax:
        a_.grid(axis="x", visible=False)
    save(fig, "fig11_gun_zaman_cizgisi")
    return {"home": h, "hub": hub, "day": str(d0)}


def fig12_audio_log():
    """Öncesi/sonrası: ham ses zarfı (çok çarpık, 1e6'ya uzanan) → log1p (dengeli)."""
    rng = np.random.default_rng(0)
    vals = []
    for h, hub in pairs():
        x = np.load(OUT / h / f"{hub}_aud.npy", mmap_mode="r")
        ok = np.flatnonzero(aud_ok(h, hub))
        if len(ok):
            vals.append(x[np.sort(rng.choice(ok, 300, replace=False))].astype("float32").ravel())
    lg = np.concatenate(vals)
    raw = np.expm1(lg)  # diskte log1p saklı; ham değer geri hesaplanır
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.4), gridspec_kw={"wspace": 0.3})
    skew = lambda v: float(pd.Series(v).skew())
    a.hist(raw, bins=120, color=MUTED, log=True)
    a.set_title("Önce: ham ses zarfı (y log ölçek)")
    a.text(0.97, 0.9, f"çarpıklık {skew(raw):.0f}\nmedyan {np.median(raw):,.0f}\nmaks {raw.max():,.0f}".replace(",", "."),
           transform=a.transAxes, ha="right", va="top", color=INK)
    a.set_xlabel("Değer"); a.set_ylabel("Örnek sayısı")
    b.hist(lg, bins=120, color=MUTED)
    b.set_title("Sonra: log1p(ses zarfı)")
    b.set_xlabel("log1p(değer)")
    b.text(0.03, 0.9, f"çarpıklık {skew(lg):.2f}", transform=b.transAxes, va="top", color=INK)
    save(fig, "fig12_ses_log")
    return {"raw_max": float(raw.max()), "raw_median": float(np.median(raw)), "skew_raw": round(skew(raw), 2),
            "skew_log": round(skew(lg), 2), "n": int(len(lg))}


def fig13_hub_normalization():
    """Öncesi/sonrası: sıcaklık hub'lar arasında kaymış (Pi ısıtıyor) → hub içi z-skoru ile hizalanır."""
    names, raw, z = [], [], []
    for h, hub in pairs():
        v = env(h, hub)[:, 1]
        v = v[~np.isnan(v)][::20]  # kutu grafiği için seyreltme yeterli
        names.append(f"{h}-{hub}"); raw.append(v); z.append(hub_z(v))
    fig, (a, b) = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    for ax, data, yl in [(a, raw, "Sıcaklık (°C)"), (b, z, "Hub içi z-skoru")]:
        ax.boxplot(data, widths=0.6, showfliers=False, patch_artist=True, boxprops={"facecolor": LIGHT, "edgecolor": MUTED},
                   medianprops={"color": INK}, whiskerprops={"color": MUTED}, capprops={"color": MUTED})
        ax.set_ylabel(yl)
        ax.grid(axis="x", visible=False)
    a.set_title("Önce: ham sıcaklık (hub'lar arası kayma)")
    b.set_title("Sonra: her hub kendi ortalaması/std'si ile ölçeklenmiş")
    b.set_xticks(range(1, len(names) + 1), names, rotation=60, ha="right", fontsize=7)
    save(fig, "fig13_hub_normalizasyon")
    med = [float(np.median(v)) for v in raw]
    return {"median_range_c": [round(min(med), 1), round(max(med), 1)]}


def fig14_label_vs_camera():
    """Etiket kalitesi: kişi sayısı = 0 iken bir kamerada insan görülmüş mü? (doğrulanmamış etiketin çapraz kontrolü)"""
    rows, cases = {}, []
    for h in HOMES:
        g = labels(h)
        Z = np.stack([img_meta(h, hub)["zone"].to_numpy() for hub in hubs_of(h)], 1)
        seen = (Z == 1).any(1)
        known = (Z >= 0).any(1)
        empty = g["number"].to_numpy() == 0
        rows[h] = {"bos_iken_kamerada_insan_%": 100 * (seen & empty).sum() / max((known & empty).sum(), 1),
                   "insan_gorulen_ama_bos_%": 100 * (seen & empty).sum() / max(seen.sum(), 1),
                   "n_celiski": int((seen & empty).sum())}
        for j, hub in enumerate(hubs_of(h)):
            for i in np.flatnonzero(empty & (Z[:, j] == 1))[:: max(1, (empty & (Z[:, j] == 1)).sum() // 2)][:2]:
                cases.append((h, hub, i, g["ts"].iloc[i]))
    df = pd.DataFrame(rows).T
    fig = plt.figure(figsize=(11, 4))
    a = fig.add_axes([0.05, 0.15, 0.38, 0.72])
    a.bar(df.index, df["bos_iken_kamerada_insan_%"], color=MUTED, width=0.6)
    for i, v in enumerate(df["bos_iken_kamerada_insan_%"]):
        a.text(i, v, f"%{v:.1f}", ha="center", va="bottom", fontsize=8)
    a.set_ylabel("Etiket 0 kişi iken\nkamerada insan (%)")
    a.set_title("Etiket ↔ kamera çelişkisi")
    a.grid(axis="x", visible=False)
    rng = np.random.default_rng(1)
    show = [cases[i] for i in rng.choice(len(cases), min(8, len(cases)), replace=False)] if cases else []
    for k, (h, hub, i, t) in enumerate(show):
        ax = fig.add_axes([0.5 + (k % 4) * 0.125, 0.52 - (k // 4) * 0.42, 0.11, 0.33])
        ax.imshow(imgs(h, hub)[i], cmap="gray", vmin=0, vmax=255)
        ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
        ax.set_xlabel(f"{h}-{hub} {t:%m-%d %H:%M}", fontsize=6, color=MUTED)
    fig.text(0.72, 0.93, "Örnek: etiket 0 kişi, kamera 'insan var' diyor", ha="center", fontweight="bold", fontsize=9)
    save(fig, "fig14_etiket_kamera")
    return df.round(2).to_dict("index")


FIGS = {f.__name__.split("_")[0]: f for f in [fig01_class_distribution, fig02_hour_of_day, fig03_segment_lengths,
                                              fig04_env_by_class, fig05_rh_cleaning, fig06_gas_floor,
                                              tab01_data_summary, fig07_completeness, fig08_example_frames,
                                              fig09_brightness_light, fig10_audio_by_class, fig11_day_timeline,
                                              fig12_audio_log, fig13_hub_normalization, fig14_label_vs_camera]}

if __name__ == "__main__":
    nums = json.loads(NUMS.read_text()) if NUMS.exists() else {}
    for k, f in FIGS.items():
        if len(sys.argv) > 1 and k not in sys.argv[1:]:
            continue
        print(k, flush=True)
        nums[f.__name__] = f()
    NUMS.write_text(json.dumps(nums, indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
