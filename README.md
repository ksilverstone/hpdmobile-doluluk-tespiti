# Görüntü, Ses ve Ortam Sensörlerinin Derin Füzyonuyla Eksik Modaliteye Dayanıklı Ev Doluluk Tespiti

Derin Öğrenme dersi multimodal dönem projesi. Veri: **HPDmobile** (University of Colorado Boulder & Iowa State University).
Görev: 10 saniyelik pencerede evde kaç kişi olduğunu sınıflandırmak — **0 / 1 / 2+**.

| Modalite | Ham hali | İşlenmiş hali |
|---|---|---|
| Görüntü | 32×32 gri PNG, saniyede 1 | pencere başına 1 kare `[T, 32, 32] uint8` |
| Ses | 10 sn'de 800 değerlik ses zarfı | `[T, 800] float16` (log1p) |
| Ortam | sıcaklık, nem, ışık, eCO2, TVOC; 10 sn | `[T, 5] float32` |
| Etiket | var/yok + kişi sayısı; 10 sn | `cls` 0/1/2+ |

## Kurulum

```bash
uv venv --python 3.12 .venv && uv pip install -p .venv -r requirements.txt
```

## Veriyi üretme

```bash
.venv/bin/python src/download.py              # küçük dosyalar (etiket, ortam, zone, karanlık liste, metadata) ~190 MB
```
Küçük zip'ler `data/interim/<ev>/` altına açılır:
```bash
cd data && for z in raw/*_{GROUNDTRUTH,ENVIRONMENTAL,ZONELABELS,DARKIMAGES}.zip; do unzip -oq "$z" -d interim/$(basename $z .zip | cut -d_ -f1); done; cd ..
```
```bash
.venv/bin/python src/build.py all --fetch     # görüntü+ses zip'lerini tek tek indir → işle → sil (~51 GB indirme, ~16 GB kalıcı)
```

## Dizin

```
src/download.py        figshare'den indirme (koleksiyon 5364449)
src/build.py           10 sn ızgarasında hizalama → data/processed/
data/raw/              indirilen zip'ler (büyükler işlenince silinir)
data/interim/<ev>/     açılmış küçük CSV'ler
data/processed/<ev>/   labels.parquet, <hub>_{env,img,aud}.npy, stats.json
data/samples/<ev>/     sunum için 1 saatlik ham görüntü + ses
docs/                  veri sorunları kaydı, araştırma notları
research/              vize yönergesi, proje seçimi taraması
```
`data/` git'e girmez.

## Kaynak

Jacoby M., Tan S.Y., Henze G., Sarkar S. (2021). A high-fidelity residential building occupancy detection dataset.
*Scientific Data* 8, 280. https://doi.org/10.1038/s41597-021-01055-x — veri lisansı CC0.
