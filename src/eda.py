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
from clean import MAX_GAP, VALID, clean_env, fill_short_gaps  # noqa: E402

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
    # görüntüde tekrar kayıt: kamera saniyede 1 kare çeker → bir pencerede 10'dan fazla kare = aynı saniyenin ikinci kopyası
    tot["img_dup_windows"] = int(sum((img_meta(h, hub)["n_frames"].to_numpy() > 10).sum() for h, hub in pairs()))
    L += ["", f"**Toplam:** {tot['img']:,} kare dosyası ({tot['img_out']:,} ızgara dışı), {tot['dark']:,} karanlık kare "
          f"(listede, görüntüsü yok), {tot['aud']:,} ses dosyası ({tot['aud_m']:,} eşleşti, {tot['aud_out']:,} ızgara dışı). "
          f"10'dan fazla karesi olan (tekrar kare içeren) pencere: {tot['img_dup_windows']:,}.", ""]
    # Bağımsız kontrol: yazarların metadata'sındaki doluluk oranları (ev başına bir hub) ile bizim sayımımız.
    # Eşleşirse dosyalar eksiksiz okunmuş ve doğru ızgaraya yerleşmiş demektir. Yazarların "Env" oranı = tam satır (NaN'sız).
    meta = pd.read_csv(ROOT / "data/interim/meta/metadata/Data_set_file_completeness.csv", encoding="utf-8-sig").dropna(subset=["Home"])
    L += ["## Yazarların metadata'sı ile karşılaştırma", "", "| Ev | Hub | Ses: yazar | Ses: biz | Ortam (tam satır): yazar | Ortam: biz |",
          "|---|---|---|---|---|---|"]
    tot["meta_max_diff"] = 0.0
    for _, r in meta.iterrows():
        h, hub = str(r["Home"]).strip(), str(r["Hub"]).strip()
        s, T = S[h], S[h]["labels"]["rows"]
        ours = (round(s[f"{hub}/aud"]["matched"] / T, 2), round((T - s[f"{hub}/env"]["any_nan"]) / T, 2))
        tot["meta_max_diff"] = max(tot["meta_max_diff"], abs(ours[0] - r["Audio"]), abs(ours[1] - r["Env"]))
        L.append(f"| {h} | {hub} | {r['Audio']:.2f} | {ours[0]:.2f} | {r['Env']:.2f} | {ours[1]:.2f} |")
    tot["meta_max_diff"] = round(tot["meta_max_diff"], 3)
    L += ["", f"En büyük fark: {tot['meta_max_diff']}.", ""]
    out = ROOT / "reports" / "veri_ozeti.md"
    out.write_text("\n".join(L))
    return tot


def tab05_class_rationale():
    """Neden 0 / 1 / 2+? (Kriter 1, 3, 4) → reports/sinif_gerekcesi.md

    Etiketteki kişi sayısı (number) sensörden değil, sakinlerin ve misafirlerin giriş-çıkış kayıtlarından gelir ve
    yazarlarca doğrulanmamıştır. İki soruya veriyle bakar:
      1) Sayı ev sakini sayısını aşıyor mu (misafir)? Sakin sayıları yazarların Home_overview.csv'sinden.
      2) Sensörler kişi sayısını ne kadar "görebiliyor"? Ölçü: en az bir kutunun kamerasında insan görülen pencere oranı
         (yazarların zone etiketi), kişi sayısına ve gece/gündüze göre. Oran 2'den sonra artmıyorsa 2, 3, 4 kişi
         sensör açısından ayırt edilemez → tek sınıfta toplamak gerekçelidir.
    """
    ho = pd.read_csv(ROOT / "data/interim/meta/metadata/Home_overview.csv", encoding="utf-8-sig")
    residents = {r["ID"]: int(str(r["Occupants"]).split()[0]) for _, r in ho.iterrows()}
    L = ["# Sınıf gerekçesi: neden 0 / 1 / 2+?", "", "`python src/eda.py tab05` ile üretilir.", "",
         "## Etiketteki kişi sayısı ve ev sakinleri", "",
         "| Ev | Sakin | Etikette en fazla | Sakin sayısını aşan pencere | 0 | 1 | 2 | 3 | 4 | 5 |", "|" + "---|" * 10]
    out, vis = {"over": {}, "counts": {}}, []
    for h in HOMES:
        g = labels(h)
        c = g["number"].value_counts().reindex(range(6), fill_value=0)
        over = int((g["number"] > residents[h]).sum())
        out["over"][h], out["counts"][h] = over, c.to_dict()
        L.append(f"| {h} | {residents[h]} | {g['number'].max()} | {over:,} ({pct(over, len(g))}%) | "
                 + " | ".join(f"{v:,}" for v in c) + " |")
        z = np.stack([img_meta(h, hub)["zone"].to_numpy() for hub in hubs_of(h)])  # -1 = zone yok
        vis.append(pd.DataFrame({"n": g["number"].clip(upper=4).to_numpy(), "gece": g["ts"].dt.hour.lt(6).to_numpy(),
                                 "gorulen": (z == 1).any(0), "bilinen": (z >= 0).any(0)}))
    d = pd.concat(vis)
    d = d[d["bilinen"]]
    t = d.groupby(["n", "gece"])["gorulen"].mean().mul(100).unstack()
    out["seen_day"], out["seen_night"] = t[False].round(1).to_dict(), t[True].round(1).to_dict()
    L += ["", "## Kamerada insan görülen pencere oranı (en az bir kutuda, %)", "",
          "| Kişi sayısı | Gündüz 06–24 | Gece 00–06 |", "|---|---|---|"]
    L += [f"| {'4+' if n == 4 else n} | {t.loc[n, False]:.1f} | {t.loc[n, True]:.1f} |" for n in t.index]
    (ROOT / "reports" / "sinif_gerekcesi.md").write_text("\n".join(L) + "\n")
    return out


def tab04_match_sample():
    """Örnek eşleştirme tablosu (zorunlu teslim: "örnek eşleştirme bilgileri") → reports/ornek_eslesme.csv

    Her evin sunum saatinin (data/samples ile aynı saat) ilk 10 dakikası; satır = (pencere, hub).
    Hangi ham kare ve ses dosyasının hangi etiket satırına bağlandığını dosya adıyla gösterir; veri indirilmeden
    açılıp okunabilir. Ses dosya adları her zaman pencerenin başlangıç saniyesini taşır (örnek saatlerde kontrol edildi).
    """
    from build import sample_hour
    rows = []
    for h in HOMES:
        g = labels(h)
        idx = np.flatnonzero((g["ts"] >= sample_hour(g)).to_numpy())[:60]  # 60 pencere = 10 dk
        for hub in hubs_of(h):
            m, a, e = img_meta(h, hub), aud_ok(h, hub), env(h, hub, clean=False)
            for i in idx:
                t, off = g["ts"].iloc[i], int(m["offset"].iloc[i])
                stamp = lambda s: (t + pd.Timedelta(seconds=s)).strftime("%Y-%m-%d_%H%M%S")
                dark = m["n_dark"].iloc[i] > 0
                rows.append({"ev": h, "pencere_no": i, "baslangic": t, "hub": hub,
                             "kare_dosyasi": f"{stamp(off)}_{hub}_{h}.png" if off >= 0 else ("(karanlık)" if dark else "(yok)"),
                             "ses_dosyasi": f"{stamp(0)}_{hub}_{h}.csv" if a[i] else "(yok)",
                             **{c: round(float(v), 2) for c, v in zip(ENV_COLS, e[i])},
                             "kisi_sayisi": int(g["number"].iloc[i]), "sinif": int(g["cls"].iloc[i])})
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "reports" / "ornek_eslesme.csv", index=False)
    # kanıt: tablodaki her dosya adı data/samples'taki ham dosyalar arasında gerçekten var mı?
    have = {p.name for p in (ROOT / "data" / "samples").rglob("*") if p.is_file()}
    names = pd.concat([df["kare_dosyasi"], df["ses_dosyasi"]])
    names = names[~names.str.startswith("(")]
    return {"rows": len(df), "files_listed": len(names), "files_found_in_samples": int(names.isin(have).sum())}


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


def md_table(df, fmt="{:,.2f}"):
    """DataFrame → markdown tablo (tabulate bağımlılığı eklememek için elle)."""
    num = lambda v: f"{int(v):,}" if float(v).is_integer() else fmt.format(v)  # tam sayı ondalıksız
    cells = [[str(i)] + [num(v) if isinstance(v, (int, float, np.floating, np.integer)) else str(v) for v in r]
             for i, r in zip(df.index, df.to_numpy())]
    head = "| " + " | ".join([df.index.name or ""] + [str(c) for c in df.columns]) + " |"
    return "\n".join([head, "|" + "---|" * (len(df.columns) + 1)] + ["| " + " | ".join(c) + " |" for c in cells])


def tab02_summary_stats():
    """Özet istatistikler (Kriter 6): her modalitenin ana değişkeni için sınıf bazında ortalama, std, çeyrekler."""
    feats = {}
    for h, hub in pairs():
        e = env(h, hub)
        cls = labels(h)["cls"].to_numpy()
        d = {ENV_TR[c]: e[:, j] for j, c in enumerate(ENV_COLS)}
        d["Kare parlaklığı (0–255)"] = brightness(h, hub)
        d["Ses enerjisi, log1p"] = aud_energy(h, hub)
        for k, v in d.items():
            feats.setdefault(k, []).append(pd.DataFrame({"v": v, "cls": cls}))
    L = ["# Özet istatistikler", "", "`python src/eda.py tab02`. Ortam değerleri temizlenmiş (aralık dışı NaN), "
         "hub'lar birleştirilmiş; NaN'lar hesaba katılmaz. n = geçerli pencere sayısı.", ""]
    out = {}
    for k, parts in feats.items():
        df = pd.concat(parts).dropna()
        t = df.groupby("cls")["v"].describe()[["count", "mean", "std", "25%", "50%", "75%", "min", "max"]]
        t.loc["hepsi"] = df["v"].describe()[["count", "mean", "std", "25%", "50%", "75%", "min", "max"]]
        t.index = [CLS_NAME.get(i, i) for i in t.index]
        t.index.name = "Sınıf"
        t.columns = ["n", "ortalama", "std", "Q1", "medyan", "Q3", "min", "maks"]
        L += [f"## {k}", "", md_table(t), ""]
        out[k] = t["medyan"].round(2).to_dict()
    (ROOT / "reports" / "ozet_istatistik.md").write_text("\n".join(L))
    return out


def tab03_cleaning_loss():
    """Temizleme dökümü (Kriter 5): her kuralın kaç değeri etkilediği, doldurma kazancı, kalan eksik."""
    n = {"toplam_hucre": 0, "ham_nan": 0, "aralik_disi": {c: 0 for c in ENV_COLS}, "rs5_nem": 0, "doldurulan": 0,
         "kalan_nan": 0, "tam_satir_once": 0, "tam_satir_sonra": 0, "satir": 0,
         "rs5disi_once": 0, "rs5disi_sonra": 0, "rs5disi_satir": 0}
    for h, hub in pairs():
        raw = env(h, hub, clean=False)
        cl = clean_env(raw, hub, ENV_COLS)
        fl = fill_short_gaps(cl)
        n["toplam_hucre"] += raw.size; n["satir"] += len(raw)
        n["ham_nan"] += int(np.isnan(raw).sum())
        for j, c in enumerate(ENV_COLS):
            lo, hi = VALID[c]
            n["aralik_disi"][c] += int(((raw[:, j] < lo) | (raw[:, j] > hi)).sum())
        if hub == "RS5":
            n["rs5_nem"] += int((~np.isnan(raw[:, 2])).sum())
        n["doldurulan"] += int(np.isnan(cl).sum() - np.isnan(fl).sum())
        n["kalan_nan"] += int(np.isnan(fl).sum())
        n["tam_satir_once"] += int((~np.isnan(raw).any(1)).sum())
        n["tam_satir_sonra"] += int((~np.isnan(fl).any(1)).sum())
        if hub != "RS5":
            n["rs5disi_once"] += int((~np.isnan(raw).any(1)).sum())
            n["rs5disi_sonra"] += int((~np.isnan(fl).any(1)).sum())
            n["rs5disi_satir"] += len(raw)
    T = n["toplam_hucre"]
    rows = [("Ham veride boş (NaN) hücre", n["ham_nan"]),
            *[(f"Aralık dışı → NaN: {ENV_TR[c]} ({VALID[c][0]}–{VALID[c][1]:g})", v) for c, v in n["aralik_disi"].items()],
            ("Takılı RS5 nem sensörü → NaN (geçerli okuma)", n["rs5_nem"]),
            (f"Kısa boşluk (≤ {MAX_GAP} pencere) doğrusal doldurulan", n["doldurulan"]),
            ("Temizleme + doldurma sonrası kalan NaN (maske)", n["kalan_nan"])]
    L = ["# Temizleme dökümü (ortam sensörleri)", "", "`python src/eda.py tab03`. Birim: hücre (pencere × sensör), "
         f"toplam {T:,} hücre = {n['satir']:,} hub-pencere × 5 sensör. Görüntü ve ses dosyalarında bozuk/şekilsiz kayıt "
         "0 (`reports/veri_ozeti.md`).", "", "| Adım | Hücre | Toplamın %'si |", "|---|---|---|"]
    L += [f"| {a} | {b:,} | {100 * b / T:.3f} |" for a, b in rows]
    L += ["", f"Beş sensörü de dolu hub-pencere: önce {n['tam_satir_once']:,} (%{100 * n['tam_satir_once'] / n['satir']:.1f}), "
          f"sonra {n['tam_satir_sonra']:,} (%{100 * n['tam_satir_sonra'] / n['satir']:.1f}). Düşüşün nedeni RS5 neminin "
          f"tamamen çıkarılması; RS5 dışındaki hub'larda tam satır oranı %{100 * n['rs5disi_once'] / n['rs5disi_satir']:.1f} → "
          f"%{100 * n['rs5disi_sonra'] / n['rs5disi_satir']:.1f} (doldurmanın kazancı).", "",
          "**Bilgi kaybı:** aralık dışı kural yalnız fiziksel olarak imkânsız okumaları siler (toplamın binde birinden az). "
          "RS5 nemi bütünüyle kaybedilir, ama aynı evde 3–4 başka hub'ın nemi kaldığı için ev düzeyinde nem bilgisi korunur. "
          "Hiçbir pencere (örnek) silinmez; eksik değer maskelenir.", ""]
    (ROOT / "reports" / "temizleme_dokumu.md").write_text("\n".join(L))
    return n


def fig15_structure():
    """Modalite yapısı (Kriter 3–4): pencere başına kare sayısı, seçilen karenin zaman farkı, ses uzunluğu."""
    nf, off, al = [], [], []
    for h, hub in pairs():
        m = img_meta(h, hub)
        nf.append(m["n_frames"].to_numpy())
        o = m["offset"].to_numpy()
        off.append(np.abs(o[o >= 0] - 5))
        al.append(pd.read_parquet(OUT / h / f"{hub}_aud.parquet")["aud_len"].to_numpy())
    nf, off, al = np.concatenate(nf), np.concatenate(off), np.concatenate(al)
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.4), gridspec_kw={"wspace": 0.35})
    for a_, v, bins, t, xl in [(ax[0], nf, np.arange(-0.5, 12), "Pencere başına kare (aydınlık)", "Kare sayısı (beklenen 10)"),
                               (ax[1], off, np.arange(-0.5, 6), "Seçilen kare pencere ortasından ne kadar uzak", "|saniye − 5|"),
                               (ax[2], al, [0, 1, 799, 801], "Ses dosyası uzunluğu", "Değer sayısı (beklenen 800)")]:
        c, _ = np.histogram(v, bins)
        x = (np.array(bins[:-1]) + np.array(bins[1:])) / 2
        labs = [f"{int(round(b))}" for b in x] if a_ is not ax[2] else ["0 (ses yok)", "1–799", "800"]
        a_.bar(range(len(c)), 100 * c / c.sum(), color=MUTED, width=0.7)
        a_.set_xticks(range(len(c)), labs)
        a_.set_title(t); a_.set_xlabel(xl); a_.grid(axis="x", visible=False)
    ax[0].set_ylabel("Pay (%)")
    save(fig, "fig15_modalite_yapisi")
    return {"frames_10_pct": round(100 * (nf == 10).mean(), 1), "frames_0_pct": round(100 * (nf == 0).mean(), 1),
            "offset_0_pct": round(100 * (off == 0).mean(), 1), "offset_le1_pct": round(100 * (off <= 1).mean(), 1),
            "aud_800_pct": round(100 * (al == 800).mean(), 1), "aud_other_nonzero": int(((al > 0) & (al != 800)).sum())}


def fig16_sample_cards():
    """Aynı örneğin dört kanalı yan yana (Kriter 4 görsel eşleştirme kanıtı, Kriter 6 modaliteler arası)."""
    h, hub = "H1", "RS2"
    g, m = labels(h), img_meta(h, hub)
    e = env(h, hub)
    rng = np.random.default_rng(3)
    ok = (m["offset"].to_numpy() >= 0) & aud_ok(h, hub) & ~np.isnan(e).any(1) & g["ts"].dt.hour.between(9, 19).to_numpy()
    z = np.stack([hub_z(e[:, j]) for j in range(5)], 1)
    x = np.load(OUT / h / f"{hub}_aud.npy", mmap_mode="r")
    fig = plt.figure(figsize=(11, 6.6))
    gs = fig.add_gridspec(3, 3, width_ratios=[0.8, 2.2, 1.4], hspace=0.55, wspace=0.3)
    out = []
    for r, k in enumerate([0, 1, 2]):
        cand = np.flatnonzero(ok & (g["cls"].to_numpy() == k) & ((m["zone"].to_numpy() == 1) | (k == 0)))
        i = int(rng.choice(cand))
        t = g["ts"].iloc[i]
        a0 = fig.add_subplot(gs[r, 0]); a0.imshow(imgs(h, hub)[i], cmap="gray", vmin=0, vmax=255)
        a0.set_xticks([]); a0.set_yticks([]); a0.grid(False)
        for sp in a0.spines.values():
            sp.set_visible(True); sp.set_color(CLS_COLOR[k]); sp.set_linewidth(3)
        a0.set_title(f"{CLS_NAME[k]} (sayı={g['number'].iloc[i]})", fontsize=9, color=INK)
        a0.set_xlabel(f"kare {t + pd.Timedelta(seconds=int(m['offset'].iloc[i])):%H:%M:%S}", fontsize=7, color=MUTED)
        a1 = fig.add_subplot(gs[r, 1]); a1.plot(np.arange(800) / 80, x[i].astype("float32"), color=MUTED, lw=0.6)
        a1.set_ylim(6, 17); a1.grid(axis="x", visible=False)
        a1.set_title(f"ses dosyası {t:%H:%M:%S} (10 sn zarf, log1p)", fontsize=8, loc="left")
        a2 = fig.add_subplot(gs[r, 2]); a2.barh(range(5), z[i], color=MUTED, height=0.6)
        a2.axvline(0, color=INK, lw=0.6); a2.set_xlim(-3, 3)
        a2.set_yticks(range(5), [ENV_TR[c].split(" (")[0] for c in ENV_COLS], fontsize=7); a2.invert_yaxis()
        a2.set_title(f"ortam {t:%H:%M:%S} (hub içi z)", fontsize=8, loc="left"); a2.grid(axis="y", visible=False)
        out.append({"cls": k, "ts": str(t), "offset_s": int(m["offset"].iloc[i]), "zone": int(m["zone"].iloc[i])})
    a1.set_xlabel("pencere içi saniye")
    fig.suptitle(f"Eşleştirilmiş örnekler: {h}-{hub}, her satır aynı 10 sn pencere [t, t+10)", fontweight="bold")
    save(fig, "fig16_ornek_kartlari")
    return out


def fig17_env_fill():
    """Öncesi/sonrası: ortam boşluklarının uzunluğu (sensör bazında) ve kısa boşlukların doğrusal doldurulması."""
    cats = ["1", "2", "3–5", "6", "7–12", "13–60", "61–360", ">360"]
    edges = [1, 2, 3, 6, 7, 13, 61, 361, np.inf]  # [a, b) aralıkları: 1 | 2 | 3–5 | 6 | 7–12 | 13–60 | 61–360 | >360
    cnt = {c: np.zeros(len(cats), int) for c in ENV_COLS}
    allg = []
    for h, hub in pairs():
        e = env(h, hub)
        for j, c in enumerate(ENV_COLS):
            d = np.diff(np.r_[0, np.isnan(e[:, j]).astype(int), 0])
            g = np.flatnonzero(d == -1) - np.flatnonzero(d == 1)
            if c == "rh_percent" and hub == "RS5":
                continue  # bilerek silinen sensör boşluk sayılmaz
            cnt[c] += np.histogram(g, edges)[0]
            allg.append(g)
    gaps = np.concatenate(allg)
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 3.8), gridspec_kw={"width_ratios": [1.2, 1.3], "wspace": 0.25})
    x = np.arange(len(cats))
    w = 0.16
    shades = ["#2b2a28", MUTED, "#85847d", LIGHT, "#d9d8d2"]
    for k, c in enumerate(ENV_COLS):
        a.bar(x + (k - 2) * w, cnt[c], w, color=shades[k], label=ENV_TR[c].split(" (")[0])
    a.set_yscale("log")
    a.axvline(3.5, color=ACCENT, lw=1.5)
    a.text(3.4, a.get_ylim()[1] * 0.3, "← doldurulur | maske →", color=ACCENT, fontsize=8, ha="center", va="top",
           bbox={"facecolor": "white", "edgecolor": "none", "pad": 1})
    a.set_xticks(x, cats, rotation=30); a.set_xlabel("Boşluk uzunluğu (pencere; 6 = 1 dk)"); a.set_ylabel("Boşluk sayısı (log)")
    a.set_title("Ortam sensörü boşlukları", pad=26); a.grid(axis="x", visible=False)
    a.legend(fontsize=7, ncol=5, loc="lower center", bbox_to_anchor=(0.5, 1.0), handlelength=1)
    h, hub = "H1", "RS1"
    e = env(h, hub)
    f = fill_short_gaps(e)
    m = np.isnan(e[:, 1]) & ~np.isnan(f[:, 1])
    i0 = max(int(np.flatnonzero(m)[len(np.flatnonzero(m)) // 2]) - 60, 0)
    sl = slice(i0, i0 + 120)
    t = labels(h)["ts"].iloc[sl]
    b.plot(t, f[sl, 1], color=LIGHT, lw=1, zorder=1)
    b.scatter(t, e[sl, 1], s=10, color=MUTED, label="ölçülen", zorder=2)
    b.scatter(t[m[sl]], f[sl, 1][m[sl]], s=18, color=ACCENT, marker="D", label="doldurulan", zorder=3)
    b.set_ylabel("Sıcaklık (°C)"); b.set_title(f"{h}-{hub}: 20 dakikalık kesit"); b.legend(loc="best")
    b.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%H:%M"))
    save(fig, "fig17_ortam_doldurma")
    return {"by_sensor": {c: dict(zip(cats, v.tolist())) for c, v in cnt.items()},
            "gaps": int(len(gaps)), "gaps_le6_pct": round(100 * (gaps <= MAX_GAP).mean(), 1),
            "cells_in_le6_pct": round(100 * gaps[gaps <= MAX_GAP].sum() / gaps.sum(), 1), "max_gap_windows": int(gaps.max())}


def fig18_bs5_case():
    """Ayrıntılı veri kalitesi vakası: normal hub (H6 BS4) ve otomatik pozlamalı hub (H6 BS5) karşılaştırması."""
    h = "H6"
    g = labels(h)
    hr = g["ts"].dt.hour.to_numpy()
    fig = plt.figure(figsize=(11, 5.2))
    gs = fig.add_gridspec(2, 4, width_ratios=[2.2, 1, 1, 0.1], hspace=0.45, wspace=0.15)
    out = {}
    for r, hub in enumerate(["BS4", "BS5"]):
        lux, br = env(h, hub)[:, 3], brightness(h, hub)
        prof = pd.DataFrame({"lux": lux, "br": br, "hr": hr}).groupby("hr").median()
        a = fig.add_subplot(gs[r, 0])
        mm = lambda v: (v - v.min()) / (v.max() - v.min())  # 0–1 ölçek: iki farklı birimin şekli tek eksende kıyaslanır
        a.plot(prof.index, mm(prof["br"]), color=INK, lw=1.8, label="kare parlaklığı")
        a.plot(prof.index, mm(prof["lux"]), color=ACCENT, lw=1.4, ls="--", label="ışık sensörü")
        a.set_ylim(-0.05, 1.05); a.set_ylabel("0–1 ölçekli saatlik medyan")
        v = ~np.isnan(lux) & ~np.isnan(br)
        rho = pd.Series(lux[v]).corr(pd.Series(br[v]), method="spearman")
        out[hub] = round(rho, 2)
        a.set_title(f"{h}-{hub}: saatlik medyan, Spearman ρ = {rho:.2f}" + ("  (normal)" if hub == "BS4" else "  (sorunlu)"),
                    loc="left")
        a.set_xticks([0, 6, 12, 18, 23])
        if r == 0:
            a.legend(loc="upper right", fontsize=7)
        else:
            a.set_xlabel("Saat")
        meta = img_meta(h, hub)["offset"].to_numpy() >= 0
        for c, hh in enumerate([2, 12]):
            idx = np.flatnonzero(meta & (hr == hh))
            i = idx[len(idx) // 2]
            ax = fig.add_subplot(gs[r, 1 + c]); ax.imshow(imgs(h, hub)[i], cmap="gray", vmin=0, vmax=255)
            ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
            ax.set_title(f"{hh:02d}:00 — {lux[i]:.0f} lux", fontsize=8)
    fig.suptitle("Vaka: H6 BS5 kamerası otomatik pozlama yüzünden ışığı izlemiyor", fontweight="bold")
    save(fig, "fig18_bs5_vaka")
    return out


FIGS = {f.__name__.split("_")[0]: f for f in [fig01_class_distribution, fig02_hour_of_day, fig03_segment_lengths,
                                              fig04_env_by_class, fig05_rh_cleaning, fig06_gas_floor,
                                              tab01_data_summary, tab04_match_sample, tab05_class_rationale, fig07_completeness, fig08_example_frames,
                                              fig09_brightness_light, fig10_audio_by_class, fig11_day_timeline,
                                              fig12_audio_log, fig13_hub_normalization, fig14_label_vs_camera,
                                              tab02_summary_stats, tab03_cleaning_loss, fig15_structure,
                                              fig16_sample_cards, fig17_env_fill, fig18_bs5_case]}

if __name__ == "__main__":
    nums = json.loads(NUMS.read_text()) if NUMS.exists() else {}
    for k, f in FIGS.items():
        if len(sys.argv) > 1 and k not in sys.argv[1:]:
            continue
        print(k, flush=True)
        nums[f.__name__] = f()
    NUMS.write_text(json.dumps(nums, indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
