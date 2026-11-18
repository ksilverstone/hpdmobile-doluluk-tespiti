"""Vize sunumu (6–7 dk, 9 slayt) → reports/sunum.pptx

PowerPoint, Keynote ve Prezi ("Start with PPTX") açabilir. Her slaytın konuşmacı notunda söylenecek metin var.
Sayılar rapordan (reports/rapor.md) alınmıştır; şekiller reports/figures/ altından.
Kullanım: .venv/bin/python src/make_slides.py
"""
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "reports" / "figures"
INK, MUTED, ACCENT = RGBColor(0x1B, 0x1B, 0x1B), RGBColor(0x52, 0x51, 0x4E), RGBColor(0x62, 0x50, 0xD6)
W, H = 13.333, 7.5

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(W), Inches(H)
BLANK = prs.slide_layouts[6]


def text(slide, x, y, w, h, lines, size=18, color=INK, bold=False):
    """lines: str listesi; '•' ile başlayan satır madde olur."""
    tf = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)).text_frame
    tf.word_wrap = True
    for i, s in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text, p.space_after = s, Pt(8)
        p.font.size, p.font.color.rgb, p.font.bold = Pt(size), color, bold
    return tf


def picture(slide, name, x, y, w, h):
    """Şekli kutuya en-boy oranını bozmadan sığdırır ve ortalar."""
    iw, ih = Image.open(FIG / name).size
    s = min(w / iw, h / ih)
    pw, ph = iw * s, ih * s
    slide.shapes.add_picture(str(FIG / name), Inches(x + (w - pw) / 2), Inches(y + (h - ph) / 2), Inches(pw), Inches(ph))


def slide(no, title, bullets, figs, notes, side=True, size=17):
    s = prs.slides.add_slide(BLANK)
    text(s, 0.5, 0.3, W - 1, 0.8, [title], size=28, bold=True)
    s.shapes.add_connector(1, Inches(0.5), Inches(1.05), Inches(W - 0.5), Inches(1.05)).line.color.rgb = ACCENT
    text(s, W - 1.2, H - 0.5, 0.8, 0.4, [str(no)], size=11, color=MUTED)
    if side:  # solda maddeler, sağda şekil(ler) alt alta
        text(s, 0.5, 1.3, 4.3, 5.8, bullets, size=size)
        n = len(figs)
        for i, f in enumerate(figs):
            picture(s, f, 5.0, 1.25 + i * 5.9 / n, 7.9, 5.9 / n - 0.1)
    else:  # üstte şekil(ler) yan yana, altta maddeler
        n = len(figs)
        for i, f in enumerate(figs):
            picture(s, f, 0.5 + i * 12.3 / n, 1.2, 12.3 / n - 0.15, 4.4)
        text(s, 0.6, 5.7, W - 1.2, 1.6, bullets, size=15)
    s.notes_slide.notes_text_frame.text = notes


# 1 — kapak
s = prs.slides.add_slide(BLANK)
text(s, 0.8, 2.0, W - 1.6, 2.2, ["Görüntü, Ses ve Ortam Sensörlerinin Derin Füzyonuyla",
                                 "Eksik Modaliteye Dayanıklı Ev Doluluk Tespiti"], size=32, bold=True)
text(s, 0.8, 4.2, W - 1.6, 0.6, ["Vize: veri toplama, eşleştirme, temizleme ve keşifsel analiz"], size=20, color=ACCENT)
text(s, 0.8, 5.3, W - 1.6, 1.2, ["Kerem Emre Gümüştaş · 231307084", "Derin Öğrenme · 19.11.2026"], size=18, color=MUTED)
s.notes_slide.notes_text_frame.text = (
    "Merhaba hocam. Projem: bir evde o an kaç kişi olduğunu kamera, mikrofon ve ortam sensörlerini birlikte kullanarak "
    "tahmin etmek. Vizede veriyi topladım, eşleştirdim, temizledim ve analiz ettim; model finalde.")

slide(2, "Problem: evde şu an kaç kişi var?",
      ["• Görev: 10 sn pencerede 0 / 1 / 2+ kişi (sınıflandırma)",
       "• Binalar dünya enerjisinin ~%30'u (IEA); doluluğa göre ısıtma %18–28 tasarruf (Lu 2010, Pang 2024)",
       "• Ama ticari sensör uyuyan kişiyi gece kaçırıyor (hata ~%100)",
       "• 3 modalite, aynı an:",
       "   görüntü (32×32 gri kare)",
       "   ses (800 değerlik ses zarfı)",
       "   ortam (sıcaklık, nem, ışık, CO2, TVOC)",
       "• Tek başına hiçbiri yetmiyor: gece kamera kör, ses gürültülü"],
      ["fig16_ornek_kartlari.png"],
      "Görevim sınıflandırma: 10 saniyelik pencerede evde 0, 1 ya da 2 ve üzeri kişi var. Neden önemli: binalar "
      "dünya enerjisinin yaklaşık üçte birini tüketiyor, evlerde en büyük kalem ısıtma. Evde kimse yokken ısıtmayı "
      "kısan akıllı termostatlar yüzde 18 ile 28 arası tasarruf sağlıyor. Ama bu, doluluğu doğru algılamaya bağlı: "
      "2024'teki bir saha testinde piyasadaki sensör uyuyan insanı gece neredeyse hiç fark edemedi. Benim projem tek "
      "sensörün kör kaldığı yerde diğer sensörlere dayanan bir model için. Sağdaki her satır aynı 10 saniyenin üç "
      "modalitesi: kare, ses, ortam. Gece kamera kör ama ses ve ortam sensörü çalışıyor.", size=15)

slide(3, "Veri: HPDmobile (figshare, açık lisans)",
      ["• Kaynak: Jacoby ve ark. 2021, Scientific Data; lisans CC0",
       "• 6 ev, 152 gün, evde 4–5 sensör kutusu",
       "• Ham: 50,9 GB zip, ~41 milyon kare",
       "• Disk yetmediği için zip'ler açılmadan, akış hâlinde işlendi",
       "• Sonuç: 1.311.925 etiketli pencere (yönerge ≥150/sınıf)",
       "   0 kişi 402.967 · 1 kişi 478.068 · 2+ 430.890",
       "• Neden 2+: kişi sayısı kapı kayıtlarından, misafir dahil; kamera 2, 3, 4 kişiyi ayırt edemiyor",
       "• Toplam dengeli, ev bazında değil: H2 ve H6'da tek kişi yaşıyor → 2+ yok"],
      ["fig01_sinif_dagilimi.png"],
      "Veriyi kendim kazımadım; açık veri havuzu figshare'den hazır aldım, yönerge buna izin veriyor. 6 ev, 152 gün. "
      "Ham veri 51 GB ve içinde 41 milyon küçük resim var; açsam 250 GB'ı geçiyordu, bilgisayarımda yer yoktu. "
      "Bu yüzden her zip'i indirip içinden okuyup işlenmiş hâlini kaydettim, zip'i sildim. Sonunda 1,3 milyon örnek, "
      "üç sınıf dengeli. Neden 2 ve üzeri: kişi sayısı sensörden değil kapı giriş-çıkış kayıtlarından geliyor ve misafirler "
      "dahil; kamerada insan görülme oranı 2, 3 ve 4 kişide aynı. Yani 2'den sonrasını sensör ayırt edemiyor. Sağdaki "
      "grafikte dikkat: H2 ve H6'da tek kişi yaşıyor, yeşil yok. Bu evler test evi olduğunda 2+ ölçülemez; bölme "
      "planında bunu dikkate aldım.", size=15)

slide(4, "Eşleştirme: hepsi aynı 10 saniyelik ızgarada",
      ["• Anahtar: (ev, zaman damgası)",
       "• Etiket ve ortam: zaten 10 sn → bire bir",
       "• Ses: dosya başına 10 sn → bire bir (%99,9 eşleşti)",
       "• Görüntü: saniyede 1 kare → pencere ortasındaki kare",
       "• Kanıt: kamera parlaklığı ile ışık sensörü aynı anda değişiyor (ρ = 0,84)",
       "• Notebook'ta ham dosya = işlenmiş satır birebir"],
      ["fig09_parlaklik_isik.png"],
      "Farklı sensörleri aynı ana bağlamak bu projenin en önemli adımı. Her şeyi etiketin 10 saniyelik ızgarasına "
      "yerleştirdim. Görüntü saniyede bir geldiği için pencerenin ortasındaki kareyi seçtim. Eşleşmenin doğru olduğunu "
      "nasıl biliyorum: iki bağımsız sensör, kamera ve ışık sensörü, aynı anda değişiyor; eşleşme kaysaydı bu uyum "
      "bozulurdu. Ayrıca notebook'ta bir ham dosyayı açıp işlenmiş veriyle birebir aynı olduğunu gösteriyorum.")

slide(5, "Eksik modalite: rastgele değil",
      ["• Üç modalitenin birlikte olduğu pencere: %53",
       "• Görüntü eksikliği gece: ışık kapalıyken yazarlar kareyi silmiş (%30,9)",
       "• H1 gece: kutuların %79'unda kare yok, pencerelerin %86'sı 2+",
       "• H6 (tek kişi) gece: %85 kare yok ama 2+ hiç yok",
       "• Risk: model 'karanlık = kalabalık' ezberleyebilir",
       "• Çözüm: pencere silinmez, her kanal için maske tutulur"],
      ["fig07_eksik_modalite.png"],
      "Her modalite her zaman yok. Üçünün birlikte olduğu pencere yaklaşık yarısı. Görüntü eksikliği rastgele değil: "
      "gece ışık kapanınca kare yok. H1'de gece kutuların çoğunda kare yok ve pencerelerin yüzde 86'sı 2+. Model "
      "'kare yoksa kalabalık' diye ezberlerse tek kişinin yaşadığı H6'da her gece yanılır. Bu bir kısayol. Projemin adı bu yüzden 'eksik modaliteye dayanıklı'. Hiçbir pencereyi silmiyorum, eksik kanalı maskeyle "
      "işaretliyorum.")

slide(6, "Temizleme: öncesi → sonrası",
      ["18 veri sorunu kayıtlı (docs/VERI_SORUNLARI.md). Nem: 128 imkânsız okuma (%3285) silindi; RS5 kutusunun nem sensörü takılı → çıkarıldı",
       "Sıcaklık: kutular farklı ısınıyor (23,9–34 °C) → kutu bazında z-skoru; ayrıca ≤1 dk boşluklar dolduruldu "
       "(tam satır %89,5 → %96,1). Ses: log dönüşümü, çarpıklık 51 → −0,7. Hiçbir örnek silinmedi."],
      ["fig05_nem_temizleme.png", "fig13_hub_normalizasyon.png"],
      "Temizlemede her adımı öncesi ve sonrasıyla gösterdim. Solda nem: bazı okumalar yüzde 3285, fiziksel olarak "
      "imkânsız, sildim. Bir kutunun nem sensörü hep aynı değeri veriyor, onu çıkardım. Sağda sıcaklık: kutuların "
      "içindeki bilgisayar ısındığı için kutular farklı sıcaklık gösteriyor; her kutuyu kendi ortalamasına göre "
      "ölçekledim, sonra hepsi aynı ölçekte. Sesi log dönüşümüyle düzelttim. Hiç örnek silmedim.", side=False)

slide(7, "Keşifsel analiz: en önemli bulgular",
      ["• Sınıf günün saatine bağlı: H1'de 2+ gece %86, öğlen %31",
       "• Aynı gün, beş kanal: ışık açılınca kamera parlıyor ve kişi görünüyor",
       "• Seste 20–30 dk'lık tekrarlayan arka plan (klima?) → ses tek başına zayıf",
       "• Ardışık pencerelerin etiketi %99,95 aynı"],
      ["fig02_saat_sinif.png", "fig11_gun_zaman_cizgisi.png"],
      "Analizde 18 grafik var; en önemlilerini gösteriyorum. Sol: 2+ sınıfı gece yığılıyor; yani sınıf ile saat "
      "karışık. Sağ: tek bir gün, beş kanal alt alta; sabah ışık açılınca kamera parlıyor, insan görünüyor, etiket "
      "değişiyor. Seste yarım saatte bir tekrarlayan bir arka plan var, muhtemelen klima; bu yüzden ses tek başına zayıf.",
      side=False)

slide(8, "Aykırı vaka: H6 BS5 kamerası",
      ["• Normal kutuda kamera parlaklığı ışığı izliyor (ρ = 0,90)",
       "• BS5'te izlemiyor (ρ = 0,02): gece öğlenden parlak",
       "• Neden: otomatik pozlama; öğlen pencereden ters ışık",
       "• Sonuç: 'parlaklık' gibi basit özellik yanıltıcı → modele ham kare verilecek",
       "• Etiket kontrolü: etiket '0 kişi' derken kamerada insan: en kötü evde %3,9",
       "• Misafir: H3'te 4 kişi yaşıyor ama misafir döneminde (23.07–04.08) '5 kişi' yazıyor → 2+ içinde kalıyor"],
      ["fig18_bs5_vaka.png"],
      "Bir aykırı durumu ayrıntılı inceledim. Normal kutuda kamera parlaklığı ışıkla birlikte artıyor. BS5'te gece "
      "öğlenden parlak. Karelere bakınca sebep belli: kamera otomatik pozlama yapıyor, öğlen pencereden gelen ışık "
      "yüzünden odayı karartıyor. Etiketleri de kontrol ettim: etiket evde kimse yok derken kamerada insan görünen "
      "pencereler en kötü evde yüzde 3,9; etiket gürültüsü düşük ama sıfır değil. Bir de misafir: H3'te dört kişi "
      "yaşıyor ama misafir geldiği iki haftada beş kişi yazıyor. 2+ sınıfı kullandığım için bu hata sınıfı değiştirmiyor.", size=16)

slide(9, "Bölme planı ve final",
      ["• Rastgele bölme sızıntı yapar: test penceresinin 10 sn öncesi eğitimde olur",
       "• Ayrıca model kişiyi değil odayı tanıyabilir",
       "• Çözüm: leave-one-home-out, 6 kat (her katta 1 ev test)",
       "• İç doğrulama: her evin son %20'si, 6 saat boşlukla",
       "• H2 ve H6 testinde 2+ yok → sınıf bazında F1 ve 6 turun birleşik karışıklık matrisi",
       "• Final: tek modalite taban çizgileri → maskeli füzyon modeli → modalite düşürme ile dayanıklılık testi"],
      [],
      "Veriyi rastgele bölemem: ardışık pencereler neredeyse aynı, rastgele bölünce model ezberler. Ayrıca aynı evin "
      "odası hem eğitimde hem testte olursa model kişiyi değil odayı tanır. Bu yüzden her seferinde bir evi tamamen "
      "teste ayırıyorum: 6 ev, 6 kat. Finalde önce her modaliteyle ayrı model, sonra birleşik model, sonra eğitimde "
      "rastgele modalite kapatarak eksik modaliteye dayanıklılığı ölçeceğim. Teşekkürler, kodu da notebook'ta "
      "gösterebilirim.", size=15)
s9 = prs.slides[-1]
rows = [("Tur", "Test evi", "Eğitim evleri", "Testte 2+")] + [
    (str(i + 1), f"H{i + 1}", ", ".join(f"H{j}" for j in range(1, 7) if j != i + 1),
     "yok" if i + 1 in (2, 6) else "var") for i in range(6)]
tbl = s9.shapes.add_table(7, 4, Inches(5.0), Inches(1.3), Inches(7.9), Inches(2.6)).table
for r, row in enumerate(rows):
    for c, v in enumerate(row):
        tbl.cell(r, c).text = v
        tbl.cell(r, c).text_frame.paragraphs[0].font.size = Pt(14)
picture(s9, "fig03_segment_sureleri.png", 5.0, 4.3, 7.9, 2.9)

out = ROOT / "reports" / "sunum.pptx"
prs.save(out)
print(out)
