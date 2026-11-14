---
konu: HPDmobile veri seti — kaynak, lisans, yapı, bilinen kısıtlar
tarih: 2026-11-14
tazelik: veri seti 2021'den beri değişmedi; kalıcı
ilgili_kod: src/download.py, src/build.py
kaynaklar:
  - https://doi.org/10.1038/s41597-021-01055-x
  - https://figshare.com/collections/_/5364449
  - https://creativecommons.org/publicdomain/zero/1.0/
---

# HPDmobile veri seti

## Kaynak ve lisans (rapor Kriter 2)

- **Makale:** Jacoby M., Tan S.Y., Henze G., Sarkar S. (2021). *A high-fidelity residential building occupancy detection
  dataset.* Scientific Data 8, 280. https://doi.org/10.1038/s41597-021-01055-x (makale CC BY 4.0)
- **Veri:** figshare koleksiyonu 5364449, 58 dosya (makale), toplam 50,9 GB zip. Lisans **CC0** (kamu malı), etik kısıt
  yok; görüntüler 336×336'dan 32×32'ye küçültülmüş, sesler konuşma anlaşılmayacak biçimde işlenmiş (kimlik gizliliği).
- Toplayan: University of Colorado Boulder + Iowa State University. Boulder, Colorado'da 6 ev, 2019.

## Yapı (doğrulandı, 2026-11-14)

| Modalite | Sıklık | Biçim | Zip düzeni |
|---|---|---|---|
| Etiket (GT) | 10 sn | `timestamp,occupied,number` — gün başına bir CSV (8640 satır) | ev başına 1 zip |
| Ortam | 10 sn | `tvoc_ppb, temp_c, rh_percent, light_lux, co2eq_ppm` (+ co2eq_base, tvoc_base) — hub×gün CSV, ölçüm yoksa satır boş | ev başına 1 zip |
| Görüntü | 1 sn | 32×32 gri PNG, `<gün>/<HHMM>/<gün>_<HHMMSS>_<hub>_<ev>.png`; karanlık kareler zip'te **yok** | hub başına 1 zip |
| Karanlık liste | — | karanlık sayılıp atılan karelerin zamanları (başlıksız CSV) | ev başına 1 zip |
| Zone etiketi | 1 sn | `timestamp,occupied` — her görüntü için "karede insan var mı" | ev başına 1 zip |
| Ses | 10 sn | 800 sayılık ses zarfı (her satır bir değer, ~1e4–1e6) — `<hub>_AUDIO/<gün>/<HHMM>/..._<HHMMSS>_...csv` | ev başına 1 zip |

Evler (metadata `Home_overview.csv`): H1 4 yetişkin+kedi, 30 gün; H2 1 yetişkin, 17; H3 4 yetişkin+köpek, 35; H4 3 yetişkin, 17;
H5 2 yetişkin+kedi, 15; H6 1 yetişkin, 38. Hub sayısı 4–5 (H2 ve H6'da 4). Doluluk oranı %47–82.

## Etiketlerin kökeni ve güvenilirliği (rapor Kriter 4)

- `occupied` (var/yok): **doğrulanmış** (makale).
- `number` (kişi sayısı): **doğrulanmamış, tahmin** (makale: "should be used as an estimate only"). Bizim 3 sınıflı hedefimiz
  (0 / 1 / 2+) buna dayanıyor → raporda kısıt olarak yazılmalı; `occupied` ile tutarlılığı ve zone etiketleriyle çapraz
  kontrolü yapılmalı. `occupied==1` ⇔ `number>0` 6 evin hepsinde 0 tutarsızlıkla sağlanıyor (2026-11-14 ölçüm).
- Zone etiketleri: önceden eğitilmiş YOLOv5 ile otomatik üretildi, tamamı doğrulanmadı, örneklem kontrolü yapıldı.
  Hub'a özel eşik `Data_set_file_completeness.csv` → `Thrsh`.

## Bilinen kısıtlar

- Yayınlanan günler ardışık değil (ör. H4 05-13..05-16 yok): yazarlar eksik günleri çıkarmış.
- H6 BS2 hub'ında ses yok (%0), H5 RS1'de ses ve ortam ~%21–22 (metadata).
- Karanlık kare oranı hub başına %0–51 (gece ışık kapalı) → görüntü modalitesi sistematik olarak eksik (eksik modalite
  sorusunun çıkış noktası).
- eCO2 zamanın büyük kısmında 400 ppm tabanında takılı (önceki tarama: %71–98) — EDA'da doğrulanacak.
- H2 ve H6 tek kişilik evler → 2+ sınıfı neredeyse yok (H2 541 satır, H6 0). Ev bazlı test bölmesinde sınıf eksikliği.

## Önceki iş (karşılaştırma için)

- Tan S.Y. ve ark., Energy & Buildings 2022: aynı veri üzerinde hiyerarşik füzyon (yazarların kendi yöntemi).
  Final aşamasında bizim derin füzyonumuzun karşılaştırma noktası.
