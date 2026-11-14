"""Modele girecek veri yapısı (Kriter 7) → reports/veri_yapisi.md

Bir örnek = (ev, 10 sn pencere). Her evde 4–5 hub var; hub'lar sabit 5 yuvaya dizilir, olmayan yuva maskelenir.
Ön işleme burada, okunurken uygulanır (diskteki veri ham hizalı kalır, öncesi/sonrası her zaman görülebilir):
    görüntü : uint8 → /255 → [0, 1] float.  Yeniden boyutlandırma yok (zaten 32×32, fig15).
    ses     : log1p (diskte) → hub içi z-skoru.  Uzunluk hep 800 (fig15), kırpma/doldurma gerekmiyor.
    ortam   : aralık dışı → NaN (clean_env) → ≤1 dk boşluk doldur (fill_short_gaps) → hub içi z → kalan NaN = 0 + maske.
Maske = "bu kanal bu pencerede gerçekten ölçüldü mü". Model eksik kanalı 0 değeriyle değil maskeyle ayırt eder.
"""
import sys, warnings
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from build import ENV_COLS, HOMES, OUT, ROOT, hubs_of  # noqa: E402
from clean import clean_env, fill_short_gaps  # noqa: E402

SLOTS = 5  # en çok hub'lı ev 5 hub'lı


@lru_cache(None)
def home(h):
    """Bir evin bütün dizileri. Büyük dosyalar mmap (yalnız istenen pencere diskten okunur)."""
    hubs = hubs_of(h)
    g = pd.read_parquet(OUT / h / "labels.parquet")
    d = {"hubs": hubs, "ts": g["ts"].to_numpy(), "y": g["cls"].to_numpy(), "number": g["number"].to_numpy(),
         "img": [], "img_ok": [], "aud": [], "aud_ok": [], "aud_stat": [], "env": [], "env_ok": []}
    for hub in hubs:
        d["img"].append(np.load(OUT / h / f"{hub}_img.npy", mmap_mode="r"))
        d["img_ok"].append(pd.read_parquet(OUT / h / f"{hub}_img.parquet")["offset"].to_numpy() >= 0)
        a = np.load(OUT / h / f"{hub}_aud.npy", mmap_mode="r")
        ok = pd.read_parquet(OUT / h / f"{hub}_aud.parquet")["aud_ok"].to_numpy()
        d["aud"].append(a); d["aud_ok"].append(ok)
        # hub içi ses istatistiği: geçerli pencerelerden seyreltilmiş örneklemle (tamamını okumak gereksiz)
        idx = np.flatnonzero(ok)[::50]
        s = a[idx].astype("float32") if len(idx) else np.zeros((1, 800), "float32")
        d["aud_stat"].append((float(s.mean()), float(s.std()) + 1e-6))
        e = fill_short_gaps(clean_env(np.load(OUT / h / f"{hub}_env.npy"), hub, ENV_COLS))
        with warnings.catch_warnings():  # RS5 nemi tümüyle NaN → "boş dilim" uyarısı beklenen durum
            warnings.simplefilter("ignore", RuntimeWarning)
            z = (e - np.nanmean(e, 0)) / (np.nanstd(e, 0) + 1e-6)
        d["env_ok"].append(~np.isnan(z)); d["env"].append(np.nan_to_num(z).astype("float32"))
    return d


def window(h, i):
    """Tek örnek → modelin gördüğü sözlük. Şekiller sabit: hub sayısı ne olursa olsun 5 yuva."""
    d = home(h)
    img = np.zeros((SLOTS, 32, 32), "float32"); aud = np.zeros((SLOTS, 800), "float32"); env = np.zeros((SLOTS, 5), "float32")
    m_img = np.zeros(SLOTS, bool); m_aud = np.zeros(SLOTS, bool); m_env = np.zeros((SLOTS, 5), bool)
    for k in range(len(d["hubs"])):
        if d["img_ok"][k][i]:
            img[k], m_img[k] = d["img"][k][i] / 255.0, True
        if d["aud_ok"][k][i]:
            mu, sd = d["aud_stat"][k]
            aud[k], m_aud[k] = (d["aud"][k][i].astype("float32") - mu) / sd, True
        env[k], m_env[k] = d["env"][k][i], d["env_ok"][k][i]
    return {"home": h, "index": i, "ts": str(pd.Timestamp(d["ts"][i])), "hubs": d["hubs"] + [None] * (SLOTS - len(d["hubs"])),
            "img": img, "aud": aud, "env": env, "mask_img": m_img, "mask_aud": m_aud, "mask_env": m_env,
            "y": int(d["y"][i]), "number": int(d["number"][i])}


def report():
    """Örnek pencerelerle girdi biçimi tablosu → reports/veri_yapisi.md"""
    w = window("H1", 100_000)
    w6 = window("H6", 100_000)  # 4 hub'lı ev: 5. yuva boş
    rows = [("img", "görüntü", w["img"], "[0, 1] float32, hub başına 1 kare"),
            ("aud", "ses zarfı", w["aud"], "hub içi z (log1p üstünde)"),
            ("env", "ortam", w["env"], "hub içi z; NaN → 0"),
            ("mask_img", "görüntü maskesi", w["mask_img"], "kare var mı (karanlık/kayıp = False)"),
            ("mask_aud", "ses maskesi", w["mask_aud"], "ses dosyası var mı"),
            ("mask_env", "ortam maskesi", w["mask_env"], "sensör değeri gerçek mi (ölçülmüş veya ≤1 dk doldurulmuş)")]
    L = ["# Modele girecek veri yapısı", "", "`python src/dataset.py` ile üretilir; kod `src/dataset.py`.", "",
         "Bir örnek = (ev, 10 sn pencere); hub'lar 5 sabit yuvaya dizilir. Etiket `y` ∈ {0, 1, 2} (0 / 1 / 2+).", "",
         "| Anahtar | Ne | Şekil | Tip | Not |", "|---|---|---|---|---|"]
    L += [f"| `{k}` | {n} | {tuple(v.shape)} | {v.dtype} | {note} |" for k, n, v, note in rows]
    L += [f"| `y` | etiket | () | int | {w['y']} (bu örnekte; kişi sayısı {w['number']}) |", "",
          "## Örnek 1: H1, pencere 100.000", "", f"- zaman: {w['ts']}, hub yuvaları: {w['hubs']}",
          f"- görüntü maskesi: {w['mask_img'].astype(int).tolist()}, ses maskesi: {w['mask_aud'].astype(int).tolist()}",
          f"- ortam maskesi (hub × sensör): {w['mask_env'].astype(int).tolist()}",
          f"- ortam (hub içi z, ilk hub): {[round(float(v), 2) for v in w['env'][0]]}", "",
          "## Örnek 2: H6, pencere 100.000 (4 hub'lı ev)", "", f"- zaman: {w6['ts']}, hub yuvaları: {w6['hubs']}",
          f"- görüntü maskesi: {w6['mask_img'].astype(int).tolist()}, ses maskesi: {w6['mask_aud'].astype(int).tolist()} "
          "(H6 BS2'de ses yok, 5. yuva boş)", "",
          "## Füzyon hazırlığı", "",
          "- **Tek modalite:** her anahtar kendi başına bir modelin girdisi olabilir (ör. yalnız `img` + `mask_img`).",
          "- **Erken füzyon:** ortam (5×5) ve ses özetleri birleştirilip tek vektör.",
          "- **Geç / ara füzyon:** her modalite kendi kodlayıcısıyla (görüntü: küçük CNN, ses: 1B CNN, ortam: MLP) gömülür, "
          "maskeli ortalama ile hub'lar ve modaliteler birleştirilir. Maske, eksik modaliteyi hesaptan çıkarır.",
          "- **Giderilecek sorunlar:** H6 BS5 kamera parlaklığı güvenilmez (fig18); ses arka plan döngüsü (fig11); "
          "günün saati ↔ sınıf karışıklığı (fig02) — finalde saat bazlı hata analizi.", ""]
    (ROOT / "reports" / "veri_yapisi.md").write_text("\n".join(L))
    return w, w6


if __name__ == "__main__":
    w, w6 = report()
    for x in (w, w6):
        assert x["img"].shape == (SLOTS, 32, 32) and x["aud"].shape == (SLOTS, 800) and x["env"].shape == (SLOTS, 5)
        assert np.isfinite(x["env"]).all() and np.isfinite(x["aud"]).all() and 0 <= x["img"].min() <= x["img"].max() <= 1
        assert x["y"] in (0, 1, 2)
    assert not w6["mask_img"][4] and not w6["mask_aud"][4] and not w6["mask_env"][4].any()  # boş yuva maskeli
    print("ok")
