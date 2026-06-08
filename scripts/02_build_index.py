#!/usr/bin/env python3
"""
Adım 2 — Vektör İndeksini Oluştur
===================================
data/chunks.jsonl dosyasını okur, her chunk'ı vektöre çevirir
ve ChromaDB'ye kaydeder.

Bu adım İNTERNET veya API GEREKTİRMEZ.
Embedding modeli (all-MiniLM-L6-v2) ilk çalıştırmada indirilir (~90 MB).

Kullanım:
    python scripts/02_build_index.py
    python scripts/02_build_index.py --reset   # indeksi sıfırdan oluştur
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pdf_processor import Chunk
from src.indexer import build_index

ROOT       = Path(__file__).resolve().parents[1]
CHUNKS_FILE = ROOT / "data" / "chunks.jsonl"
INDEX_DIR   = ROOT / "data" / "chroma_db"


def load_chunks(path: Path) -> list[Chunk]:
    chunks = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            c = Chunk(
                chunk_id=d["chunk_id"],
                ders=d["ders"],
                donem=d["donem"],
                kaynak_dosya=d["kaynak_dosya"],
                sayfa_baslangic=d["sayfa_baslangic"],
                sayfa_bitis=d["sayfa_bitis"],
                tip=d["tip"],
                metin=d["metin"],
            )
            chunks.append(c)
    return chunks


def main():
    parser = argparse.ArgumentParser(description="ChromaDB indeksi oluştur")
    parser.add_argument("--reset", action="store_true",
                        help="Mevcut indeksi sil, sıfırdan oluştur")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  Beykent Matematik RAG — Adım 2: İndeks Oluşturma")
    print(f"{'='*60}\n")

    if not CHUNKS_FILE.exists():
        print("[!] chunks.jsonl bulunamadı. Önce Adım 1'i çalıştırın:")
        print("    python scripts/01_process_pdfs.py\n")
        sys.exit(1)

    print(f"[→] Chunk'lar yükleniyor: {CHUNKS_FILE}")
    t0 = time.perf_counter()
    chunks = load_chunks(CHUNKS_FILE)
    print(f"[✓] {len(chunks)} chunk yüklendi.\n")

    # Ders istatistikleri
    ders_sayisi: dict[str, int] = {}
    tip_sayisi:  dict[str, int] = {}
    for c in chunks:
        ders_sayisi[c.ders] = ders_sayisi.get(c.ders, 0) + 1
        tip_sayisi[c.tip]   = tip_sayisi.get(c.tip, 0) + 1

    print("Ders dağılımı:")
    for ders, n in sorted(ders_sayisi.items()):
        print(f"  {ders:<35s}: {n:>5} chunk")

    print("\nBölüm tipi dağılımı:")
    for tip, n in sorted(tip_sayisi.items()):
        print(f"  {tip:<15s}: {n:>5} chunk")

    print(f"\n[→] ChromaDB indeksi oluşturuluyor: {INDEX_DIR}")
    print("    İlk çalıştırmada embedding modeli indiriliyor (~90 MB)...\n")

    added = build_index(chunks, persist_dir=INDEX_DIR, reset=args.reset)

    elapsed = time.perf_counter() - t0
    print(f"\n{'='*60}")
    print(f"  Tamamlandı: {added} chunk indekslendi")
    print(f"  Süre: {elapsed:.1f}s")
    print(f"  İndeks: {INDEX_DIR}")
    print(f"{'='*60}\n")
    print("Sonraki adım:")
    print("  python scripts/03_query.py \"Cauchy teoremi nedir?\"\n")


if __name__ == "__main__":
    main()
