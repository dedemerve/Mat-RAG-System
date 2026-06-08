"""
indexer.py
==========
Chunk listesini ChromaDB vektör veritabanına yazar.

Kullanım:
    from src.indexer import build_index, load_collection
    n = build_index(chunks, persist_dir="data/chroma_db")
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.pdf_processor import Chunk

COLLECTION_NAME = "mat_knowledge_base"
EMBED_MODEL     = "all-MiniLM-L6-v2"   # Ücretsiz, API gerektirmez
BATCH_SIZE      = 100


def build_index(
    chunks: list[Chunk],
    persist_dir: str | Path = "data/chroma_db",
    reset: bool = False,
) -> int:
    """
    Chunk listesini ChromaDB'ye yazar. İndeksi diske kaydeder.

    Parametreler
    ------------
    chunks      : process_pdf() çıktısı
    persist_dir : ChromaDB'nin saklanacağı klasör
    reset       : True ise mevcut koleksiyonu siler ve yeniden oluşturur

    Döner
    -----
    Eklenen chunk sayısı
    """
    try:
        import chromadb
        from chromadb.utils import embedding_functions
    except ImportError:
        raise SystemExit(
            "ChromaDB eksik. Lütfen kurun:\n  pip install chromadb sentence-transformers"
        )

    persist_dir = Path(persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)

    # Eğer sıfırdan başlamak isteniyorsa eski indeksi sil
    if reset and persist_dir.exists():
        import shutil
        shutil.rmtree(persist_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)
        print(f"[!] Eski indeks silindi: {persist_dir}")

    client = chromadb.PersistentClient(path=str(persist_dir))

    # Ücretsiz embedding modeli — İngilizce + Türkçe semantik arama yapar
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBED_MODEL
    )

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    # Mevcut chunk ID'lerini al (resume desteği)
    existing_ids: set[str] = set()
    try:
        existing = collection.get(include=[])
        existing_ids = set(existing["ids"])
    except Exception:
        pass

    # Yeni chunk'ları filtrele
    new_chunks = [c for c in chunks if c.chunk_id not in existing_ids]
    if not new_chunks:
        print(f"[=] Eklenecek yeni chunk yok ({len(existing_ids)} mevcut).")
        return 0

    ids       = [c.chunk_id for c in new_chunks]
    documents = [c.metin    for c in new_chunks]
    metadatas: list[dict[str, Any]] = [
        {
            "ders":              c.ders,
            "donem":             c.donem,
            "kaynak_dosya":      c.kaynak_dosya,
            "sayfa_baslangic":   c.sayfa_baslangic,
            "sayfa_bitis":       c.sayfa_bitis,
            "tip":               c.tip,          # tanim/teorem/ispat/ornek/alistirma/metin
            "token_tahmini":     c.token_tahmini,
        }
        for c in new_chunks
    ]

    # Toplu ekleme (ChromaDB batch limiti nedeniyle parça parça)
    added = 0
    for start in range(0, len(ids), BATCH_SIZE):
        end = start + BATCH_SIZE
        collection.upsert(
            ids=ids[start:end],
            documents=documents[start:end],
            metadatas=metadatas[start:end],
        )
        added += end - start
        print(f"  [{added}/{len(ids)}] chunk eklendi...", end="\r")

    print(f"\n[✓] {added} yeni chunk indekslendi. Toplam: {len(existing_ids) + added}")

    # Manifest dosyası yaz
    manifest = {
        "collection":   COLLECTION_NAME,
        "embed_model":  EMBED_MODEL,
        "total_chunks": len(existing_ids) + added,
        "persist_dir":  str(persist_dir),
    }
    (persist_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return added


def load_collection(persist_dir: str | Path = "data/chroma_db"):
    """Daha önce oluşturulan koleksiyonu yükler."""
    try:
        import chromadb
        from chromadb.utils import embedding_functions
    except ImportError:
        raise SystemExit("ChromaDB eksik: pip install chromadb sentence-transformers")

    client = chromadb.PersistentClient(path=str(persist_dir))
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBED_MODEL
    )
    return client.get_collection(name=COLLECTION_NAME, embedding_function=ef)
