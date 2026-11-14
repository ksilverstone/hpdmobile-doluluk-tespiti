"""Keşifsel veri analizi (EDA) grafikleri → reports/figures/*.png

Her fonksiyon bir şekil üretir ve rapora girecek sayıları döndürür (reports/eda_numbers.json).
Kullanım: python src/eda.py            # hepsi
          python src/eda.py fig02      # tek şekil
"""
import json, sys
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


FIGS = {f.__name__.split("_")[0]: f for f in [fig01_class_distribution, fig02_hour_of_day, fig03_segment_lengths,
                                              fig04_env_by_class, fig05_rh_cleaning, fig06_gas_floor]}

if __name__ == "__main__":
    nums = json.loads(NUMS.read_text()) if NUMS.exists() else {}
    for k, f in FIGS.items():
        if len(sys.argv) > 1 and k not in sys.argv[1:]:
            continue
        print(k, flush=True)
        nums[f.__name__] = f()
    NUMS.write_text(json.dumps(nums, indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
