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

Python 3.12 gerekir.
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```
(`uv` kuruluysa: `uv venv --python 3.12 .venv && uv pip install -p .venv -r requirements.txt`)

## Veriyi üretme

```bash
.venv/bin/python src/download.py              # küçük dosyalar (etiket, ortam, zone, karanlık liste, metadata) ~190 MB
```
Küçük zip'ler `data/interim/<ev>/` altına açılır:
```bash
cd data && for z in raw/*_{GROUNDTRUTH,ENVIRONMENTAL,ZONELABELS,DARKIMAGES}.zip; do unzip -oq "$z" -d interim/$(basename $z .zip | cut -d_ -f1); done; cd ..
```
```bash
.venv/bin/python src/build.py all --fetch     # görüntü+ses zip'lerini tek tek indir → işle → sil (~51 GB indirme, ~15 GB kalıcı)
```

## Analiz, rapor ve notebook

```bash
.venv/bin/python src/eda.py                   # 18 grafik + tablolar → reports/ (~1 dk); tek grafik: src/eda.py fig07
.venv/bin/python src/split.py                 # bölme planı → reports/bolme_plani.md
.venv/bin/python src/dataset.py               # modele girecek örnek yapısı → reports/veri_yapisi.md
.venv/bin/python src/clean.py                 # temizleme kurallarının öz-testi ("ok")
.venv/bin/jupyter lab notebooks/vize_eda.ipynb  # notebook; Run → Run All Cells
```

## Dizin

```
src/download.py        figshare'den indirme (koleksiyon 5364449)
src/build.py           10 sn ızgarasında hizalama → data/processed/
src/clean.py           temizleme kuralları (okunurken uygulanır)
src/eda.py             EDA grafikleri + tablolar (+ ornek_eslesme.csv, sinif_gerekcesi.md) → reports/ (`python src/eda.py [fig07 tab01 ...]`)
src/split.py           bölme planı (leave-one-home-out + zamansal doğrulama) → reports/bolme_plani.md
src/dataset.py         modele girecek örnek yapısı (5 hub yuvası + maskeler) → reports/veri_yapisi.md
notebooks/vize_eda.ipynb  sunum notebook'u: ham dosya ↔ işlenmiş dizi kanıtı + bütün grafikler
reports/rapor.md       vize teknik raporu (PDF: reports/rapor.pdf ← src/export_pdf.py)
reports/sunum.pptx     vize sunumu, konuşmacı notlu (← src/make_slides.py)
reports/               figures/*.png, veri_ozeti.md, ozet_istatistik.md, temizleme_dokumu.md, bolme_plani.md, veri_yapisi.md, eda_numbers.json
data/raw/              indirilen zip'ler (büyükler işlenince silinir)
data/interim/<ev>/     açılmış küçük CSV'ler
data/processed/<ev>/   labels.parquet, <hub>_{env,img,aud}.npy, stats.json
data/samples/<ev>/     sunum için 1 saatlik ham görüntü + ses
docs/                  veri sorunları kaydı, araştırma notları
```
`data/` git'e girmez.

## Kaynak

Jacoby M., Tan S.Y., Henze G., Sarkar S. (2021). A high-fidelity residential building occupancy detection dataset.
*Scientific Data* 8, 280. https://doi.org/10.1038/s41597-021-01055-x — veri lisansı CC0.
