# Veri sorunları kaydı

Veride bulunan her sorun buraya yazılır: ne, nerede, kaç kayıt, kök neden, ne yaptık, durum. Raporun **Kriter 5 (temizleme)**
ve **Kriter 6 (aykırı durum analizi)** bölümleri bu tablodan yazılır. Bir temizleme adımına başlamadan önce buraya bak.
En yeni üstte. Sayılar `data/processed/<ev>/stats.json`'dan gelir; elle yazılan sayı kaynağıyla birlikte yazılır.

Durum: **açık** (henüz ele alınmadı) · **ele alındı** (yöntem uygulandı, sonucu ölçüldü) · **kabul** (düzeltilemez, raporda kısıt).

| Tarih | Sorun | Nerede / kaç kayıt | Kök neden | Ne yaptık | Durum |
|---|---|---|---|---|---|
| 2026-11-14 | Fiziksel olarak imkânsız nem/sıcaklık değerleri | nem ~3285 %rH (hub başına 10–31 okuma, ör. H2 RS1 10, H6 BS3 31); iç mekânda −12,7 °C (H6 BS3) | DHT22 sensörünün okuma hatası (taşma değeri) | aralık dışı (nem 0–100, sıcaklık 0–45) → NaN (`src/clean.py`); toplam 128 nem okuması; öncesi/sonrası `fig05` | ele alındı |
| 2026-11-14 | RS5 kutusunun nem sensörü takılı | H2–H5 RS5: nem std 0,4–0,7, hep %48–51 (diğer hub'larda std 3–33) | aynı fiziksel RS5 cihazı evden eve taşınmış; nem sensörü arızalı | RS5 nemi NaN (`src/clean.py`, H1 RS5 dahil: 30–55, 57 farklı değer); `fig05` sağ panel | ele alındı |
| 2026-11-14 | Sıcaklık mutlak değeri güvenilmez | H2 (Mart ayı) 30–36 °C, bütün evlerde hub'lar arası 2–4 °C fark | kutunun içindeki Raspberry Pi ısıtıyor | mutlak değer yerine hub bazlı normalizasyon | açık |
| 2026-11-14 | eCO2 ve TVOC çoğunlukla taban değerde | eCO2=400 ppm hub başına %21–98, TVOC=0 %21–98 | SGP30 sensörünün alt sınırı 400 ppm; düşük konsantrasyonu ayırt edemiyor | `fig06` (taban payı), `fig04` (sınıflar arası kutular üst üste) → bilgi taşıma kapasitesi düşük; final'de özellik ablasyonuyla karar | açık |
| 2026-11-14 | Sınıf ile günün saati karışık (confound) | H1'de 2+ sınıfı gece 00–05'te %87, öğlen %30 | çok kişilik evlerde gece herkes evde ve uyuyor; ışık kapalı | model "karanlık = 2+" kısayolunu öğrenebilir → EDA'da gösterilecek, finalde saat bazlı hata analizi | kabul |
| 2026-11-14 | H5 RS1 ortam verisinin çoğu yok | %79 satırda boş | donanım kesintisi (metadata %21 tamlık) | maske; hub düşürme EDA'dan sonra karar | açık |
| 2026-11-14 | Kişi sayısı etiketi doğrulanmamış | tüm evler, `number` sütunu | yazarlar yalnız var/yok'u doğrulamış (makale) | 3 sınıflı hedefte kısıt olarak raporlanacak; zone etiketiyle çapraz kontrol yapılacak | açık |
| 2026-11-14 | Karanlık kareler zip'te yok | hub başına %0–51 (metadata `% Dark`); H4 RS4: 498.429 karanlık / 816.571 mevcut kare | gece ışık kapalı → yazarlar ortalama piksel eşiğiyle atmış | pencere başına `n_dark` sayılıyor, görüntü maskesi 0; eksik modalite olarak modellenecek | ele alındı (sayım) |
| 2026-11-14 | Ortam sensöründe boş satırlar | H2 hub başına 10.753–13.484 satırda en az bir değer boş; H4 RS4 7.467 satır tamamen boş | sensör/hub kesintisi | NaN olarak tutuluyor; doldurma yöntemi EDA'dan sonra seçilecek | açık |
| 2026-11-14 | 2+ sınıfı tek kişilik evlerde yok | H2 541 satır, H6 0 | H2 ve H6'da tek yetişkin yaşıyor | bölme stratejisinde dikkate alınacak (Kriter 7) | kabul |
| 2026-11-14 | Bazı hub'larda ses yok/az | H6 BS2 %0, H5 RS1 %22 (metadata) | donanım kesintisi | `aud_ok` maskesi | ele alındı (maske) |
| 2026-11-14 | Ses zarfı değer aralığı çok geniş (~1e4–1e6) | tüm ses | ham şiddet değerleri | `log1p` + float16 (float16 65.504'ü aşamaz) | ele alındı |
