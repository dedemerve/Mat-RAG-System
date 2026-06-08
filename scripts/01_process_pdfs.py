#!/usr/bin/env python3
"""
Adım 1 — PDF'leri İşle
======================
data/kitaplar/ altındaki tüm PDF'leri okur, chunk'lara böler
ve data/chunks.jsonl dosyasına yazar.

Kullanım:
    python scripts/01_process_pdfs.py
    python scripts/01_process_pdfs.py --ders "Topoloji I"   # sadece bir ders
    python scripts/01_process_pdfs.py --dry-run             # ne yapacağını göster
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Proje kökünü path'e ekle
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import yaml
except ImportError:
    raise SystemExit("PyYAML eksik: pip install pyyaml")

from src.pdf_processor import process_pdf, Chunk

ROOT       = Path(__file__).resolve().parents[1]
KITAP_DIR  = ROOT / "data" / "kitaplar"
OUTPUT     = ROOT / "data" / "chunks.jsonl"
CONFIG     = ROOT / "config" / "dersler.yaml"


def load_config() -> list[dict]:
    with open(CONFIG, encoding="utf-8") as f:
        return yaml.safe_load(f)["dersler"]


def chunk_to_dict(c: Chunk) -> dict:
    return {
        "chunk_id":          c.chunk_id,
        "ders":              c.ders,
        "donem":             c.donem,
        "kaynak_dosya":      c.kaynak_dosya,
        "sayfa_baslangic":   c.sayfa_baslangic,
        "sayfa_bitis":       c.sayfa_bitis,
        "tip":               c.tip,
        "token_tahmini":     c.token_tahmini,
        "metin":             c.metin,
    }


def main():
    parser = argparse.ArgumentParser(description="PDF'leri chunk'lara böl")
    parser.add_argument("--ders",    help="Sadece bu dersi işle")
    parser.add_argument("--dry-run", action="store_true", help="Gerçek işlem yapma")
    args = parser.parse_args()

    dersler = load_config()
    if args.ders:
        dersler = [d for d in dersler if args.ders.lower() in d["ders"].lower()]
        if not dersler:
            print(f"[!] '{args.ders}' adında ders bulunamadı.")
            sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  Beykent Matematik RAG — Adım 1: PDF İşleme")
    print(f"{'='*60}\n")

    total_chunks = 0
    total_pdfs   = 0
    t0 = time.perf_counter()

    # Mevcut chunk ID'lerini yükle (resume desteği)
    existing_ids: set[str] = set()
    if OUTPUT.exists():
        with open(OUTPUT, encoding="utf-8") as f:
            for line in f:
                try:
                    existing_ids.add(json.loads(line)["chunk_id"])
                except Exception:
                    pass
        print(f"[=] Mevcut chunk'lar: {len(existing_ids)} (atlanacak)\n")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT, "a", encoding="utf-8") as out_f:
        for ders_conf in dersler:
            klasor = KITAP_DIR / ders_conf["klasor"]
            ders   = ders_conf["ders"]
            donem  = ders_conf["donem"]

            if not klasor.exists():
                print(f"[?] Klasör bulunamadı, atlanıyor: {klasor}")
                continue

            pdfs = list(klasor.glob("*.pdf"))
            if not pdfs:
                print(f"[?] PDF yok: {klasor}")
                continue

            print(f"📚 {ders} ({donem}) — {len(pdfs)} PDF")

            for pdf_path in pdfs:
                if args.dry_run:
                    print(f"   [dry-run] {pdf_path.name}")
                    continue

                try:
                    chunks = process_pdf(pdf_path, ders=ders, donem=donem)
                    new_chunks = [c for c in chunks if c.chunk_id not in existing_ids]

                    for c in new_chunks:
                        out_f.write(json.dumps(chunk_to_dict(c), ensure_ascii=False) + "\n")
                        existing_ids.add(c.chunk_id)

                    total_chunks += len(new_chunks)
                    total_pdfs   += 1
                    print(f"   ✓ {pdf_path.name}: {len(new_chunks)} yeni chunk")

                except Exception as e:
                    print(f"   ✗ {pdf_path.name}: HATA — {e}")

    elapsed = time.perf_counter() - t0
    print(f"\n{'='*60}")
    print(f"  Tamamlandı: {total_pdfs} PDF, {total_chunks} yeni chunk")
    print(f"  Süre: {elapsed:.1f}s")
    print(f"  Çıktı: {OUTPUT}")
    print(f"{'='*60}\n")
    print("Sonraki adım:")
    print("  python scripts/02_build_index.py\n")


if __name__ == "__main__":
    main()
