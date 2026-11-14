"""Veri bölme planı (Kriter 7) → reports/bolme_plani.md

Neden rastgele (stratified) 5-fold değil:
  1. Zaman komşuluğu: art arda iki pencerenin etiketi %99,95 aynı (fig03). Rastgele bölmede test penceresinin
     10 sn öncesi/sonrası eğitimde olur → model "ezber" ile yüksek skor alır, gerçek başarı ölçülmez.
  2. Ev kimliği: aynı ev = aynı odalar, aynı kamera açısı, aynı kişiler. Görüntü modeli kişiyi değil odayı tanıyabilir.
Bu yüzden:
  * Dış döngü — leave-one-home-out (LOHO, grup tabanlı 6 kat): her katta 1 ev test, kalan 5 ev eğitim.
    Bir pencerenin bütün modaliteleri (görüntü, ses, ortam, etiket) aynı satırda → aynı katta kalır.
  * İç doğrulama — eğitim evlerinin her birinin son %20 günü doğrulama (zamansal), arada 6 saat boşluk.
    6 saat: 2+ sınıfı segmentlerinin medyanı 364 dk (fig03); boşluk, sınırdaki aynı segmentin iki tarafa düşmesini önler.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from build import HOMES, OUT, ROOT  # noqa: E402

VAL_FRAC = 0.2
GAP = pd.Timedelta("6h")


def labels(h):
    return pd.read_parquet(OUT / h / "labels.parquet")


def inner_split(ts):
    """Bir evin zaman damgaları → 'train' / 'gap' / 'val' etiketleri (kronolojik; günün ortasından bölünür)."""
    cut = ts.iloc[0] + (ts.iloc[-1] - ts.iloc[0]) * (1 - VAL_FRAC)
    part = np.where(ts >= cut, "val", "train").astype(object)
    part[(ts >= cut - GAP) & (ts < cut)] = "gap"
    return part


def folds():
    """Her kat: test evi, eğitim evleri."""
    for test in HOMES:
        yield {"test": test, "train": [h for h in HOMES if h != test]}


def counts(c):
    v = pd.Series(c).value_counts().reindex([0, 1, 2], fill_value=0)
    return v.tolist()


def report():
    G = {h: labels(h) for h in HOMES}
    P = {h: inner_split(G[h]["ts"]) for h in HOMES}
    L = ["# Bölme planı", "", "`python src/split.py` ile üretilir. Gerekçe: `src/split.py` başındaki açıklama, fig03.", "",
         "Sayılar = 10 sn pencere, sınıf sırası 0 / 1 / 2+. İç bölme: her eğitim evinin son %20'si doğrulama, "
         "öncesindeki 6 saat atılır (gap).", "",
         "| Kat | Test evi | Eğitim (0/1/2+) | Doğrulama (0/1/2+) | Gap'te atılan | Test (0/1/2+) | Testte 2+ var mı |",
         "|---|---|---|---|---|---|---|"]
    for k, f in enumerate(folds(), 1):
        tr = np.concatenate([G[h]["cls"].to_numpy()[P[h] == "train"] for h in f["train"]])
        va = np.concatenate([G[h]["cls"].to_numpy()[P[h] == "val"] for h in f["train"]])
        gap = sum(int((P[h] == "gap").sum()) for h in f["train"])
        te = counts(G[f["test"]]["cls"])
        fmt = lambda v: " / ".join(f"{x:,}" for x in v)
        L.append(f"| {k} | {f['test']} | {fmt(counts(tr))} | {fmt(counts(va))} | {gap:,} | {fmt(te)} | "
                 f"{'evet' if te[2] / sum(te) >= 0.01 else f'yok sayılır ({te[2]}, %{100 * te[2] / sum(te):.1f})'} |")
    L += ["", "## Kurallar", "",
          "- **Sızıntı:** aynı ev hem eğitimde hem testte olmaz; doğrulama eğitimden zamanca sonra gelir ve arada 6 saat boşluk var.",
          "- **Normalizasyon:** her hub kendi verisinin ortalama/std'si ile ölçeklenir (fig13). Etiket kullanılmaz, "
          "bu yüzden test evinin istatistiğini hesaplamak etiket sızıntısı değildir (gözetimsiz uyarlama). Katı alternatif: "
          "test evinde yalnız ilk 24 saatin istatistiği — finalde ikisi karşılaştırılacak.",
          "- **H2 ve H6 test katları:** 2+ sınıfı yok (H2'de 541, H6'da 0). Bu katlarda 3 sınıflı macro-F1 tanımsız olur; "
          "sınıf bazında F1 ve 6 katın birleşik (pooled) karışıklık matrisi raporlanacak.",
          "- **Sınıf dengesi:** eğitimde sınıf payları dengeli (~%30–37); ağırlıklandırma gerekirse eğitim katının sayılarından hesaplanır.",
          "- **Eksik modalite:** pencere silinmez; her modalite için maske taşınır (fig07). Finalde eğitim sırasında "
          "rastgele modalite düşürme (modality dropout) ile eksik modaliteye dayanıklılık ölçülecek.", ""]
    (ROOT / "reports" / "bolme_plani.md").write_text("\n".join(L))
    return G, P


if __name__ == "__main__":
    G, P = report()
    for h in HOMES:
        ts, p = G[h]["ts"], P[h]
        assert ts[p == "train"].max() + GAP <= ts[p == "val"].min() + pd.Timedelta("10s"), h  # boşluk korunuyor
        assert set(p) == {"train", "gap", "val"}
    for f in folds():
        assert f["test"] not in f["train"] and len(f["train"]) == 5
    print("ok")
