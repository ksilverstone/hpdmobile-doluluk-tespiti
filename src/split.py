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


def leakage_table(G=None, P=None, seed=0):
    """Sızıntıyı sayıyla gösterir: rastgele bölme ile bizim bölmemizi karşılaştırır.

    Ölçü 1 — komşu oranı: test penceresinin 10 sn öncesi ya da sonrası eğitimde mi?
    Ölçü 2 — "komşuyu kopyala" doğruluğu: hiçbir şey öğrenmeyen, test penceresine zamanca en yakın EĞİTİM
    penceresinin etiketini söyleyen hile. Bu yüksekse bölme sızdırıyor demektir (sahte başarı).
    """
    G = G or {h: labels(h) for h in HOMES}
    P = P or {h: inner_split(G[h]["ts"]) for h in HOMES}

    def cheat(ts, y, is_train, is_test):
        """Aynı evde: test pencerelerinin komşu oranı ve en yakın eğitim penceresinin etiketiyle doğruluk."""
        t = ts.to_numpy().astype("datetime64[s]").astype("int64")  # saniye (birim dtype'tan bağımsız)
        tr_t, tr_y = t[is_train], y[is_train]
        te_t, te_y = t[is_test], y[is_test]
        if len(tr_t) == 0 or len(te_t) == 0:
            return 0, 0, len(te_t)
        i = np.clip(np.searchsorted(tr_t, te_t), 1, len(tr_t) - 1)
        left_closer = (te_t - tr_t[i - 1]) <= (tr_t[i] - te_t)
        j = np.where(left_closer, i - 1, i)
        dist = np.abs(tr_t[j] - te_t)
        return int((dist <= 10).sum()), int((tr_y[j] == te_y).sum()), len(te_t)

    rows = []
    # A) Rastgele %80 / %20 (pencere bazında) — yapmadığımız bölme
    rng = np.random.default_rng(seed)
    nb = ok = n = 0
    for h in HOMES:
        y = G[h]["cls"].to_numpy(); te = rng.random(len(y)) < 0.2
        a, b, c = cheat(G[h]["ts"], y, ~te, te); nb += a; ok += b; n += c
    rows.append(("Rastgele %80/%20 (yapmadığımız)", n, round(100 * nb / n, 2), round(100 * ok / n, 2)))
    # B) Bizim iç doğrulama: aynı evde eğitim → 6 saat boşluk → doğrulama
    nb = ok = n = 0
    for h in HOMES:
        y = G[h]["cls"].to_numpy()
        a, b, c = cheat(G[h]["ts"], y, P[h] == "train", P[h] == "val"); nb += a; ok += b; n += c
    rows.append(("Bizim doğrulama (son %20, 6 sa boşluk)", n, round(100 * nb / n, 2), round(100 * ok / n, 2)))
    # C) Bizim test: leave-one-home-out — test evinde hiç eğitim penceresi yok
    n = sum(len(G[h]) for h in HOMES)
    rows.append(("Bizim test (leave-one-home-out)", n, 0.0, "uygulanamaz: test evinde eğitim penceresi yok"))
    return pd.DataFrame(rows, columns=["Bölme", "Değerlendirilen pencere", "Komşusu eğitimde (%)",
                                       "'Komşuyu kopyala' hilesinin doğruluğu (%)"])


if __name__ == "__main__":
    G, P = report()
    for h in HOMES:
        ts, p = G[h]["ts"], P[h]
        assert ts[p == "train"].max() + GAP <= ts[p == "val"].min() + pd.Timedelta("10s"), h  # boşluk korunuyor
        assert set(p) == {"train", "gap", "val"}
    for f in folds():
        assert f["test"] not in f["train"] and len(f["train"]) == 5
    L = leakage_table(G, P)
    assert L.iloc[0, 3] > 99 and L.iloc[1, 2] == 0 and L.iloc[2, 2] == 0  # rastgele sızdırır, bizimki sızdırmaz
    print("ok")
