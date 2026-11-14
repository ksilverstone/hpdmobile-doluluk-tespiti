"""Temizleme kuralları. Her kuralın gerekçesi docs/VERI_SORUNLARI.md'de.

İşlenmiş veri (data/processed) ham hizalanmış hâlde kalır; temizleme okunurken uygulanır.
Böylece öncesi/sonrası karşılaştırması her zaman yapılabilir.
"""
import numpy as np

# fiziksel olarak mümkün aralıklar (iç mekân); dışı = sensör okuma hatası
VALID = {"temp_c": (0, 45), "rh_percent": (0, 100), "light_lux": (0, 1e5), "co2eq_ppm": (400, 60000),
         "tvoc_ppb": (0, 60000)}
STUCK_RH_HUBS = {"RS5"}  # H1–H5'te dolaşan RS5 cihazının nem sensörü takılı (std < 1)


def clean_env(x, hub, cols):
    """x: [T, 5] ham ortam dizisi → aralık dışı değerler NaN, takılı sensör NaN. Kopya döner."""
    x = x.copy()
    for j, c in enumerate(cols):
        lo, hi = VALID[c]
        bad = (x[:, j] < lo) | (x[:, j] > hi)
        x[bad, j] = np.nan
        if c == "rh_percent" and hub in STUCK_RH_HUBS:
            x[:, j] = np.nan
    return x


MAX_GAP = 6  # 6 pencere = 1 dakika. Boşlukların %77'si bu kadar kısa (fig17); ortam ölçümü 1 dk'da az değişir.


def fill_short_gaps(x, max_len=MAX_GAP):
    """Her sütunda en fazla max_len pencerelik NaN boşluğunu iki yanındaki değerden doğrusal doldurur.

    Uzun boşluk dokunulmadan NaN kalır (orada değer uydurmak gerçek veri gibi görünen sahte veri olur) → maske.
    Baştaki/sondaki boşluk doldurulmaz: bir yanı yoksa ara değer de yoktur. Kopya döner.
    """
    x = x.copy()
    t = np.arange(len(x))
    for j in range(x.shape[1]):
        m = np.isnan(x[:, j])
        if not m.any() or m.all():
            continue
        d = np.diff(np.r_[0, m.astype(int), 0])
        short = np.zeros(len(x), bool)
        for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)):  # a: boşluk başı, b: bitişten sonraki
            if b - a <= max_len and a > 0 and b < len(x):
                short[a:b] = True
        x[short, j] = np.interp(t[short], t[~m], x[~m, j])
    return x


if __name__ == "__main__":
    cols = ["tvoc_ppb", "temp_c", "rh_percent", "light_lux", "co2eq_ppm"]
    x = np.array([[0, 25, 3285, 10, 400], [5, -12.7, 40, 20, 450]], "float32")
    y = clean_env(x, "RS1", cols)
    assert np.isnan(y[0, 2]) and np.isnan(y[1, 1]) and y[1, 2] == 40 and y[0, 1] == 25
    assert np.isnan(clean_env(x, "RS5", cols)[:, 2]).all()
    g = np.array([[1], [np.nan], [np.nan], [4], [np.nan] * 1, [6]] + [[np.nan]] * 8 + [[9]], "float32")
    f = fill_short_gaps(g)
    assert np.allclose(f[:6, 0], [1, 2, 3, 4, 5, 6]) and np.isnan(f[6:14, 0]).all() and f[14, 0] == 9
    print("ok")
