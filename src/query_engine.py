"""
query_engine.py
===============
RAG sorgu motoru.

Kullanım (sadece retrieval — API gerektirmez):
    python scripts/03_query.py "Cauchy teoremi nedir?"

Kullanım (LLM ile cevap — OpenAI API gerekir):
    python scripts/03_query.py "Cauchy teoremi nedir?" --llm
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

# Cosine mesafe eşiği: 0.0 = aynı, 1.0 = tamamen farklı
# 0.70 altı = anlamlı eşleşme, üzeri = sistem "bulunamadı" der
MAX_DISTANCE = 0.72
N_RESULTS    = 10

SYSTEM_PROMPT = """Sen Beykent Üniversitesi Matematik Bölümü öğrencilerine yardımcı olan
bir akademik asistansın. Cevaplarını YALNIZCA sağlanan kaynak belgelerine dayandır.
Kaynakta olmayan hiçbir şeyi uydurma — bilgi yoksa bunu açıkça söyle.

Cevap formatı:
1. Kısa ve net açıklama
2. Varsa kaynak ders + sayfa numarası
3. Varsa ilgili diğer derslerle bağlantı

Türkçe yaz. Akademik ama anlaşılır ol."""


def _build_filters(question: str) -> dict[str, Any] | None:
    """
    Sorudan otomatik filtre çıkar.
    Belirli bir ders adı geçiyorsa o derse yönlendir.
    """
    q = question.lower()

    ders_map = {
        "topoloji":             "Topoloji",
        "kompleks analiz":      "Kompleks Analiz",
        "complex analysis":     "Kompleks Analiz",
        "lineer cebir":         "Lineer Cebir I",
        "linear algebra":       "Lineer Cebir I",
        "diferansiyel":         "Diferansiyel Denklemler",
        "differential":         "Diferansiyel Denklemler",
        "sayısal analiz":       "Sayısal Analiz I",
        "numerical":            "Sayısal Analiz I",
        "olasılık":             "Olasılık Teorisi",
        "probability":          "Olasılık Teorisi",
        "reel analiz":          "Reel Analiz",
        "real analysis":        "Reel Analiz",
        "fonksiyonel analiz":   "Fonksiyonel Analiz",
        "functional analysis":  "Fonksiyonel Analiz",
        "analiz":               "Matematiksel Analiz",
        "calculus":             "Matematiksel Analiz",
    }

    # Tip filtresi (sadece tanımlar, teoremler, vb.)
    tip_map = {
        "tanım":    "tanim",
        "teorem":   "teorem",
        "ispat":    "ispat",
        "örnek":    "ornek",
        "alıştırma": "alistirma",
        "exercise": "alistirma",
        "problem":  "alistirma",
    }

    filters: dict[str, str] = {}

    # Ders filtresi
    for keyword, ders_adi in ders_map.items():
        if keyword in q:
            filters["ders"] = ders_adi
            break

    # Tip filtresi (örn. "...tanımı nedir?" → sadece tanım bloklarına bak)
    for keyword, tip_adi in tip_map.items():
        if keyword in q:
            filters["tip"] = tip_adi
            break

    if not filters:
        return None
    if len(filters) == 1:
        return filters
    # Birden fazla filtre varsa $and kullan
    return {"$and": [{k: v} for k, v in filters.items()]}


def retrieve(
    question: str,
    persist_dir: str | Path = "data/chroma_db",
    n_results: int = N_RESULTS,
) -> list[dict[str, Any]]:
    """
    Soruya anlamca en yakın chunk'ları döner.

    Döner
    -----
    [
        {
            "id":       "topoloji_ch_0042",
            "metin":    "Tanım 2.3. Metrik uzay ...",
            "distance": 0.45,
            "ders":     "Topoloji I",
            "tip":      "tanim",
            "sayfa":    47,
        },
        ...
    ]
    """
    from src.indexer import load_collection

    collection = load_collection(persist_dir)

    where = _build_filters(question)
    kwargs: dict[str, Any] = {
        "query_texts": [question],
        "n_results":   n_results,
        "include":     ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where

    try:
        result = collection.query(**kwargs)
    except Exception:
        # Filtre sonuç vermezse filtresiz dene
        kwargs.pop("where", None)
        result = collection.query(**kwargs)

    hits: list[dict[str, Any]] = []
    if not result["ids"] or not result["ids"][0]:
        return hits

    for i, doc_id in enumerate(result["ids"][0]):
        distance = (result.get("distances") or [[None]])[0][i]
        if distance is not None and distance > MAX_DISTANCE:
            continue  # Halüsinasyon koruması: çok uzak sonuçları at

        meta = (result.get("metadatas") or [[{}]])[0][i] or {}
        hits.append({
            "id":       doc_id,
            "metin":    (result.get("documents") or [[""]])[0][i],
            "distance": round(distance, 4) if distance is not None else None,
            "ders":     meta.get("ders", "?"),
            "donem":    meta.get("donem", "?"),
            "tip":      meta.get("tip", "metin"),
            "sayfa":    meta.get("sayfa_baslangic", "?"),
            "kaynak":   meta.get("kaynak_dosya", "?"),
        })

    return hits


def answer_with_llm(question: str, hits: list[dict[str, Any]]) -> str:
    """
    Retrieval sonuçlarını OpenAI'ye göndererek doğal dil cevabı üretir.
    OPENAI_API_KEY ortam değişkeni gerekir.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY bulunamadı.\n"
            "Lütfen .env dosyanıza ekleyin: OPENAI_API_KEY=sk-..."
        )

    try:
        from openai import OpenAI
    except ImportError:
        raise SystemExit("OpenAI kütüphanesi eksik: pip install openai")

    if not hits:
        return (
            "## Kaynak bulunamadı\n\n"
            f"'{question}' sorusu için bilgi tabanında anlamlı eşleşme yok.\n"
            "Lütfen soruyu farklı kelimelerle deneyin."
        )

    # Bağlamı oluştur
    context_parts = []
    for h in hits[:6]:  # En iyi 6 chunk yeterli
        context_parts.append(
            f"[Kaynak: {h['ders']}, Sayfa {h['sayfa']}, Tip: {h['tip']}]\n{h['metin']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"Soru: {question}\n\nKaynaklar:\n{context}"},
        ],
        temperature=0.2,
        max_tokens=800,
    )
    return response.choices[0].message.content or ""


def format_results(hits: list[dict[str, Any]]) -> str:
    """Retrieval sonuçlarını okunabilir formatta döner (LLM olmadan)."""
    if not hits:
        return "Sonuç bulunamadı. Soruyu farklı kelimelerle deneyin."

    lines = [f"{'='*60}", f"  {len(hits)} sonuç bulundu", f"{'='*60}"]
    for i, h in enumerate(hits, 1):
        lines.append(
            f"\n[{i}] {h['ders']}  ·  Sayfa {h['sayfa']}  ·  {h['tip'].upper()}"
            f"  ·  benzerlik: {1 - (h['distance'] or 0):.0%}"
        )
        lines.append("-" * 50)
        # Metni 300 karakterle sınırla
        metin = h["metin"][:300]
        if len(h["metin"]) > 300:
            metin += "..."
        lines.append(metin)

    return "\n".join(lines)
