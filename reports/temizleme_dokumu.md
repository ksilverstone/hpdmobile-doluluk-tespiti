# Temizleme dökümü (ortam sensörleri)

`python src/eda.py tab03`. Birim: hücre (pencere × sensör), toplam 30,422,125 hücre = 6,084,425 hub-pencere × 5 sensör. Görüntü ve ses dosyalarında bozuk/şekilsiz kayıt 0 (`reports/veri_ozeti.md`).

| Adım | Hücre | Toplamın %'si |
|---|---|---|
| Ham veride boş (NaN) hücre | 2,105,487 | 6.921 |
| Aralık dışı → NaN: TVOC (ppb) (0–60000) | 0 | 0.000 |
| Aralık dışı → NaN: Sıcaklık (°C) (0–45) | 3 | 0.000 |
| Aralık dışı → NaN: Bağıl nem (%) (0–100) | 128 | 0.000 |
| Aralık dışı → NaN: Işık (lux) (0–100000) | 1,049 | 0.003 |
| Aralık dışı → NaN: eCO2 (ppm) (400–60000) | 0 | 0.000 |
| Takılı RS5 nem sensörü → NaN (geçerli okuma) | 901,575 | 2.964 |
| Kısa boşluk (≤ 6 pencere) doğrusal doldurulan | 991,440 | 3.259 |
| Temizleme + doldurma sonrası kalan NaN (maske) | 2,016,802 | 6.629 |

Beş sensörü de dolu hub-pencere: önce 5,465,099 (%89.8), sonra 4,903,610 (%80.6). Düşüşün nedeni RS5 neminin tamamen çıkarılması; RS5 dışındaki hub'larda tam satır oranı %89.5 → %96.1 (doldurmanın kazancı).

**Bilgi kaybı:** aralık dışı kural yalnız fiziksel olarak imkânsız okumaları siler (toplamın binde birinden az). RS5 nemi bütünüyle kaybedilir, ama aynı evde 3–4 başka hub'ın nemi kaldığı için ev düzeyinde nem bilgisi korunur. Hiçbir pencere (örnek) silinmez; eksik değer maskelenir.
