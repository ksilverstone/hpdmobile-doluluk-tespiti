# Modele girecek veri yapısı

`python src/dataset.py` ile üretilir; kod `src/dataset.py`.

Bir örnek = (ev, 10 sn pencere); hub'lar 5 sabit yuvaya dizilir. Etiket `y` ∈ {0, 1, 2} (0 / 1 / 2+).

| Anahtar | Ne | Şekil | Tip | Not |
|---|---|---|---|---|
| `img` | görüntü | (5, 32, 32) | float32 | [0, 1] float32, hub başına 1 kare |
| `aud` | ses zarfı | (5, 800) | float32 | hub içi z (log1p üstünde) |
| `env` | ortam | (5, 5) | float32 | hub içi z; NaN → 0 |
| `mask_img` | görüntü maskesi | (5,) | bool | kare var mı (karanlık/kayıp = False) |
| `mask_aud` | ses maskesi | (5,) | bool | ses dosyası var mı |
| `mask_env` | ortam maskesi | (5, 5) | bool | sensör değeri gerçek mi (ölçülmüş veya ≤1 dk doldurulmuş) |
| `y` | etiket | () | int | 2 (bu örnekte; kişi sayısı 4) |

## Örnek 1: H1, pencere 100.000

- zaman: 2019-12-07 13:46:40, hub yuvaları: ['RS1', 'RS2', 'RS3', 'RS4', 'RS5']
- görüntü maskesi: [1, 1, 1, 1, 1], ses maskesi: [1, 1, 1, 1, 1]
- ortam maskesi (hub × sensör): [[1, 1, 1, 1, 1], [1, 1, 1, 1, 1], [1, 1, 1, 1, 1], [1, 1, 1, 1, 1], [1, 1, 0, 1, 1]]
- ortam (hub içi z, ilk hub): [-0.08, 1.55, 1.06, 0.82, -0.06]

## Örnek 2: H6, pencere 100.000 (4 hub'lı ev)

- zaman: 2019-10-23 13:46:40, hub yuvaları: ['BS2', 'BS3', 'BS4', 'BS5', None]
- görüntü maskesi: [1, 1, 1, 1, 0], ses maskesi: [0, 1, 0, 1, 0] (H6 BS2'de ses yok, 5. yuva boş)

## Füzyon hazırlığı

- **Tek modalite:** her anahtar kendi başına bir modelin girdisi olabilir (ör. yalnız `img` + `mask_img`).
- **Erken füzyon:** ortam (5×5) ve ses özetleri birleştirilip tek vektör.
- **Geç / ara füzyon:** her modalite kendi kodlayıcısıyla (görüntü: küçük CNN, ses: 1B CNN, ortam: MLP) gömülür, maskeli ortalama ile hub'lar ve modaliteler birleştirilir. Maske, eksik modaliteyi hesaptan çıkarır.
- **Giderilecek sorunlar:** H6 BS5 kamera parlaklığı güvenilmez (fig18); ses arka plan döngüsü (fig11); günün saati ↔ sınıf karışıklığı (fig02) — finalde saat bazlı hata analizi.
