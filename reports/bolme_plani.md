# Bölme planı

`python src/split.py` ile üretilir. Gerekçe: `src/split.py` başındaki açıklama, fig03.

Sayılar = 10 sn pencere, sınıf sırası 0 / 1 / 2+. İç bölme: her eğitim evinin son %20'si doğrulama, öncesindeki 6 saat atılır (gap).

| Kat | Test evi | Eğitim (0/1/2+) | Doğrulama (0/1/2+) | Gap'te atılan | Test (0/1/2+) | Testte 2+ var mı |
|---|---|---|---|---|---|---|
| 1 | H1 | 244,351 / 326,681 / 207,864 | 107,951 / 89,376 / 67,057 | 10,800 | 45,921 / 58,866 / 153,058 | evet |
| 2 | H2 | 239,747 / 295,405 / 332,516 | 101,867 / 90,121 / 94,589 | 10,800 | 58,150 / 88,189 / 541 | yok sayılır (541, %0.4) |
| 3 | H3 | 237,452 / 328,610 / 194,470 | 94,971 / 89,220 / 54,002 | 10,800 | 65,800 / 55,632 / 180,968 | evet |
| 4 | H4 | 269,232 / 316,953 / 288,395 | 102,063 / 85,804 / 91,798 | 10,800 | 26,928 / 72,499 / 47,453 | evet |
| 5 | H5 | 258,803 / 315,870 / 306,819 | 108,857 / 108,102 / 73,074 | 10,800 | 31,606 / 49,124 / 48,870 | evet |
| 6 | H6 | 189,010 / 230,366 / 332,516 | 36,811 / 88,972 / 95,130 | 10,800 | 174,562 / 153,758 / 0 | yok sayılır (0, %0.0) |

## Kurallar

- **Sızıntı:** aynı ev hem eğitimde hem testte olmaz; doğrulama eğitimden zamanca sonra gelir ve arada 6 saat boşluk var.
- **Normalizasyon:** her hub kendi verisinin ortalama/std'si ile ölçeklenir (fig13). Etiket kullanılmaz, bu yüzden test evinin istatistiğini hesaplamak etiket sızıntısı değildir (gözetimsiz uyarlama). Katı alternatif: test evinde yalnız ilk 24 saatin istatistiği — finalde ikisi karşılaştırılacak.
- **H2 ve H6 test katları:** 2+ sınıfı yok (H2'de 541, H6'da 0). Bu katlarda 3 sınıflı macro-F1 tanımsız olur; sınıf bazında F1 ve 6 katın birleşik (pooled) karışıklık matrisi raporlanacak.
- **Sınıf dengesi:** eğitimde sınıf payları dengeli (~%30–37); ağırlıklandırma gerekirse eğitim katının sayılarından hesaplanır.
- **Eksik modalite:** pencere silinmez; her modalite için maske taşınır (fig07). Finalde eğitim sırasında rastgele modalite düşürme (modality dropout) ile eksik modaliteye dayanıklılık ölçülecek.
