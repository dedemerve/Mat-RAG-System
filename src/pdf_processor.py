"""
pdf_processor.py
================
PDF dosyasını okur, anlamlı parçalara (chunk) böler ve her parçayı etiketler.

Desteklenen bölüm tipleri:
    - tanim    : Tanım / Definition
    - teorem   : Teorem, Lemma, Önerme, Corollary
    - ispat    : İspat / Proof
    - ornek    : Örnek / Example
    - alistirma: Alıştırma / Exercise / Problem
    - metin    : Genel paragraf (yukarıdakilere girmeyen)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    raise SystemExit(
        "PyMuPDF eksik. Lütfen kurun:\n  pip install pymupdf"
    )


# ── Bölüm tipi tespiti için regex kalıpları ──────────────────────────────────
_PATTERNS: dict[str, re.Pattern] = {
    "tanim": re.compile(
        r"^\s*(tanım|definition|def\.?)\s*[\d.]*\s*[.:)]",
        re.IGNORECASE | re.MULTILINE,
    ),
    "teorem": re.compile(
        r"^\s*(teorem|theorem|lemma|önerme|proposition|corollary|sonuç)\s*[\d.]*\s*[.:)]",
        re.IGNORECASE | re.MULTILINE,
    ),
    "ispat": re.compile(
        r"^\s*(ispat|proof|kanıt)\s*[.:)]",
        re.IGNORECASE | re.MULTILINE,
    ),
    "ornek": re.compile(
        r"^\s*(örnek|example|ex\.?)\s*[\d.]*\s*[.:)]",
        re.IGNORECASE | re.MULTILINE,
    ),
    "alistirma": re.compile(
        r"^\s*(alıştırma|exercise|problem|soru)\s*[\d.]*\s*[.:)]",
        re.IGNORECASE | re.MULTILINE,
    ),
}


@dataclass
class Chunk:
    """Bir PDF parçasını temsil eder."""
    chunk_id: str          # ör. "topoloji_1_ch_0042"
    ders: str              # ör. "Topoloji I"
    donem: str             # ör. "5. Yarıyıl"
    kaynak_dosya: str      # PDF dosya adı
    sayfa_baslangic: int
    sayfa_bitis: int
    tip: str               # tanim / teorem / ispat / ornek / alistirma / metin
    metin: str             # chunk'ın ham metni
    token_tahmini: int = field(init=False)

    def __post_init__(self):
        # Basit token tahmini: kelime sayısı × 1.3
        self.token_tahmini = int(len(self.metin.split()) * 1.3)


def _detect_type(text: str) -> str:
    """Metnin başına bakarak bölüm tipini tespit eder."""
    for tip, pattern in _PATTERNS.items():
        if pattern.search(text[:200]):
            return tip
    return "metin"


def _clean(text: str) -> str:
    """Metni temizler: gereksiz boşluklar, sayfa numaraları vb."""
    # Çok sayıda boşluğu tek boşluğa indir
    text = re.sub(r" {3,}", "  ", text)
    # Sadece sayıdan oluşan satırları (sayfa numarası) kaldır
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)
    # 3+ ardışık yeni satırı tek satır yap
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def process_pdf(
    pdf_path: Path,
    ders: str,
    donem: str,
    chunk_min_chars: int = 150,
    chunk_max_chars: int = 1500,
) -> list[Chunk]:
    """
    Bir PDF dosyasını okur ve Chunk listesi döner.

    Parametreler
    ------------
    pdf_path       : PDF dosyasının yolu
    ders           : Ders adı (ör. "Topoloji I")
    donem          : Dönem (ör. "5. Yarıyıl")
    chunk_min_chars: Bu uzunluktan kısa parçalar atlanır
    chunk_max_chars: Bu uzunluktan uzun parçalar bölünür

    Döner
    -----
    list[Chunk]
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF bulunamadı: {pdf_path}")

    doc = fitz.open(str(pdf_path))
    stem = pdf_path.stem[:40].replace(" ", "_")

    chunks: list[Chunk] = []
    chunk_idx = 0

    # Her sayfayı paragraf bloklarına ayır
    buffer_text = ""
    buffer_start_page = 1

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_text = page.get_text("text")  # type: ignore[arg-type]
        page_text = _clean(page_text)

        if not page_text:
            continue

        # Paragraf sınırlarında böl
        paragraphs = re.split(r"\n{2,}", page_text)

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Buffer'a ekle
            buffer_text += "\n\n" + para if buffer_text else para

            # Yeterince büyüdüyse chunk oluştur
            if len(buffer_text) >= chunk_max_chars:
                if len(buffer_text) >= chunk_min_chars:
                    tip = _detect_type(buffer_text)
                    chunks.append(Chunk(
                        chunk_id=f"{stem}_ch_{chunk_idx:04d}",
                        ders=ders,
                        donem=donem,
                        kaynak_dosya=pdf_path.name,
                        sayfa_baslangic=buffer_start_page,
                        sayfa_bitis=page_num + 1,
                        tip=tip,
                        metin=buffer_text[:chunk_max_chars],
                    ))
                    chunk_idx += 1
                buffer_text = buffer_text[chunk_max_chars:]
                buffer_start_page = page_num + 1

        # Yeni bölüm başlığı varsa mevcut buffer'ı kapat
        if re.search(r"^\s*(chapter|bölüm|section|kısım)\s+\d", page_text,
                     re.IGNORECASE | re.MULTILINE):
            if buffer_text and len(buffer_text) >= chunk_min_chars:
                tip = _detect_type(buffer_text)
                chunks.append(Chunk(
                    chunk_id=f"{stem}_ch_{chunk_idx:04d}",
                    ders=ders,
                    donem=donem,
                    kaynak_dosya=pdf_path.name,
                    sayfa_baslangic=buffer_start_page,
                    sayfa_bitis=page_num + 1,
                    tip=tip,
                    metin=buffer_text,
                ))
                chunk_idx += 1
            buffer_text = ""
            buffer_start_page = page_num + 2

    # Son kalan buffer'ı ekle
    if buffer_text and len(buffer_text) >= chunk_min_chars:
        tip = _detect_type(buffer_text)
        chunks.append(Chunk(
            chunk_id=f"{stem}_ch_{chunk_idx:04d}",
            ders=ders,
            donem=donem,
            kaynak_dosya=pdf_path.name,
            sayfa_baslangic=buffer_start_page,
            sayfa_bitis=len(doc),
            tip=tip,
            metin=buffer_text,
        ))

    doc.close()
    return chunks
