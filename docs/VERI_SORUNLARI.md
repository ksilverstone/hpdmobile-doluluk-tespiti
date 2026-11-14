# Veri sorunları kaydı

Veride bulunan her sorun buraya yazılır: ne, nerede, kaç kayıt, kök neden, ne yaptık, durum. Raporun **Kriter 5 (temizleme)**
ve **Kriter 6 (aykırı durum analizi)** bölümleri bu tablodan yazılır. Bir temizleme adımına başlamadan önce buraya bak.
En yeni üstte. Sayılar `data/processed/<ev>/stats.json`'dan gelir; elle yazılan sayı kaynağıyla birlikte yazılır.

Durum: **açık** (henüz ele alınmadı) · **ele alındı** (yöntem uygulandı, sonucu ölçüldü) · **kabul** (düzeltilemez, raporda kısıt).

| Tarih | Sorun | Nerede / kaç kayıt | Kök neden | Ne yaptık | Durum |
|---|---|---|---|---|---|
| 2026-11-14 | Kişi sayısı etiketi doğrulanmamış | tüm evler, `number` sütunu | yazarlar yalnız var/yok'u doğrulamış (makale) | 3 sınıflı hedefte kısıt olarak raporlanacak; zone etiketiyle çapraz kontrol yapılacak | açık |
| 2026-11-14 | Karanlık kareler zip'te yok | hub başına %0–51 (metadata `% Dark`); H4 RS4: 498.429 karanlık / 816.571 mevcut kare | gece ışık kapalı → yazarlar ortalama piksel eşiğiyle atmış | pencere başına `n_dark` sayılıyor, görüntü maskesi 0; eksik modalite olarak modellenecek | ele alındı (sayım) |
| 2026-11-14 | Ortam sensöründe boş satırlar | H2 hub başına 10.753–13.484 satırda en az bir değer boş; H4 RS4 7.467 satır tamamen boş | sensör/hub kesintisi | NaN olarak tutuluyor; doldurma yöntemi EDA'dan sonra seçilecek | açık |
| 2026-11-14 | 2+ sınıfı tek kişilik evlerde yok | H2 541 satır, H6 0 | H2 ve H6'da tek yetişkin yaşıyor | bölme stratejisinde dikkate alınacak (Kriter 7) | kabul |
| 2026-11-14 | Bazı hub'larda ses yok/az | H6 BS2 %0, H5 RS1 %22 (metadata) | donanım kesintisi | `aud_ok` maskesi | ele alındı (maske) |
| 2026-11-14 | Ses zarfı değer aralığı çok geniş (~1e4–1e6) | tüm ses | ham şiddet değerleri | `log1p` + float16 (float16 65.504'ü aşamaz) | ele alındı |
