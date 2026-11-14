"""HPDmobile indirici (figshare collection 5364449).

Kullanım:
    python src/download.py            # küçük dosyalar (GT, env, zone, dark, metadata)
    python src/download.py --all      # + ses ve görüntü (~50 GB)
    python src/download.py --homes H1 H2 --all

Dosyalar data/raw/<ad>.zip olarak iner; aynı boyutta dosya varsa atlanır.
"""
import argparse, json, urllib.request
from pathlib import Path

COLLECTION = 5364449
API = "https://api.figshare.com/v2"
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def get(url):
    return json.load(urllib.request.urlopen(url))


def list_files():
    for art in get(f"{API}/collections/{COLLECTION}/articles?page_size=100"):
        for f in get(f"{API}/articles/{art['id']}")["files"]:
            yield art["title"], f["name"], f["size"], f["download_url"], f["computed_md5"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="ses ve görüntü dahil")
    ap.add_argument("--homes", nargs="*", default=None)
    args = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    files = sorted(list_files(), key=lambda f: f[2])  # küçükten büyüğe
    manifest = []
    for title, name, size, url, md5 in files:
        big = "Audio" in title or "Image Data" in title
        if big and not args.all:
            continue
        if args.homes and not any(h in title for h in args.homes) and "Metadata" not in title:
            continue
        # görüntü zip adları hub'a göre çakışabilir → başlıktan benzersiz ad
        out = RAW / (name if not "Image Data" in title else f"{title.split()[1]}_{title.split()[-1]}_IMAGES.zip")
        manifest.append({"title": title, "file": out.name, "size": size, "md5": md5, "url": url})
        if out.exists() and out.stat().st_size == size:
            continue
        print(f"{size/1e6:9.1f} MB  {out.name}", flush=True)
        tmp = out.with_suffix(".part")
        urllib.request.urlretrieve(url, tmp)
        tmp.rename(out)
    (RAW / "manifest.json").write_text(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()
