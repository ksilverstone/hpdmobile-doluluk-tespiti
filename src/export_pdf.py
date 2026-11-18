"""Teknik raporu PDF'e çevirir: reports/rapor.md → reports/rapor.pdf (şekiller gömülü).

Yol: Markdown → HTML (python-markdown) → Chrome'un "yazdır → PDF" özelliği (görünmez, ayrı geçici profil;
kullanıcının Chrome profiline dokunmaz). pandoc/LaTeX kurmaya gerek kalmaz.
Kullanım: .venv/bin/python src/export_pdf.py
"""
import re, subprocess, tempfile
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
REP = ROOT / "reports"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# akademik görünüm: A4, serif metin, numaralı şekil/tablo zaten metinde; tablolar ince çizgili
CSS = """
@page { size: A4; margin: 18mm 16mm; }
body { font-family: 'Times New Roman', Georgia, serif; font-size: 10.5pt; line-height: 1.4; color: #111; }
h1 { font-size: 17pt; text-align: center; margin: 0 0 6pt; }
h2 { font-size: 13pt; margin-top: 16pt; border-bottom: 1px solid #999; page-break-after: avoid; }
h3 { font-size: 11.5pt; margin-top: 10pt; page-break-after: avoid; }
p, li { text-align: justify; }
table { border-collapse: collapse; width: 100%; font-size: 8.5pt; margin: 6pt 0; page-break-inside: avoid; }
th, td { border: 1px solid #aaa; padding: 2pt 4pt; text-align: left; }
th { background: #eee; }
img { display: block; max-width: 100%; max-height: 120mm; margin: 8pt auto 2pt; page-break-inside: avoid; }
code { font-family: Menlo, monospace; font-size: 8.5pt; }
pre { background: #f5f5f5; padding: 6pt; font-size: 7.5pt; white-space: pre-wrap; }
hr { border: 0; border-top: 1px solid #ccc; }
"""


def fix_lists(text):
    """python-markdown listeden önce boş satır ve iç içe listede 4 boşluk ister; GitHub istemez → farkı kapat."""
    out, prev = [], ""
    for line in text.splitlines():
        if re.match(r"^  [-*] ", line):
            line = "  " + line  # iç içe madde: 2 → 4 boşluk
        is_item = re.match(r"^\s*([-*]|\d+\.) ", line)
        if is_item and prev.strip() and not re.match(r"^\s*([-*]|\d+\.) ", prev) and not prev.startswith(" "):
            out.append("")
        out.append(line)
        prev = line
    return "\n".join(out)


def main():
    body = markdown.markdown(fix_lists((REP / "rapor.md").read_text()), extensions=["tables", "fenced_code"])
    html = REP / "_rapor.html"  # resimler göreli yol (figures/...) → HTML reports/ içinde olmalı
    html.write_text(f"<!doctype html><html lang='tr'><head><meta charset='utf-8'><style>{CSS}</style></head>"
                    f"<body>{body}</body></html>")
    with tempfile.TemporaryDirectory() as prof:
        subprocess.run([CHROME, "--headless=new", f"--user-data-dir={prof}", "--no-pdf-header-footer",
                        f"--print-to-pdf={REP / 'rapor.pdf'}", html.as_uri()], check=True, capture_output=True)
    html.unlink()
    print(REP / "rapor.pdf")


if __name__ == "__main__":
    main()
