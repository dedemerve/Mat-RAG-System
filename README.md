# Matematik RAG

** İstanbul Beykent Üniversitesi Matematik Bölümü müfredatı için RAG (Retrieval-Augmented Generation) sistemi.**

Ders kitaplarınızı sisteme yükleyin, tüm müfredatı doğal dil soruları ile sorgulayın.

> *"Cauchy teoreminin ispat adımları neler?"*
> *"Limit kavramı Analiz I, Topoloji ve Fonksiyonel Analiz'de nasıl farklılaşıyor?"*
> *"Runge-Kutta yöntemi ile analitik çözümün farkı nedir?"*

---

## Nasıl Çalışır?

```
PDF Kitapları → Chunk'lara Böl → Vektöre Çevir → ChromaDB → Soru Sor
```

1. **`01_process_pdfs.py`** — PDF'leri okur, tanım/teorem/ispat/örnek bloklarına böler
2. **`02_build_index.py`** — Her bloğu vektöre çevirerek ChromaDB'ye kaydeder
3. **`03_query.py`** — Doğal dil sorusu alır, en ilgili kaynak paragrafları getirir

---

## Kurulum

### Gereksinimler
- Python 3.10+
- ~200 MB disk alanı (embedding modeli için)

```bash
git clone https://github.com/dedemerve/beykent-mat-rag
cd beykent-mat-rag
pip install -r requirements.txt
```

---

## Kullanım

### 1. PDF'leri Ekle

`data/kitaplar/` altında her ders için bir klasör oluşturun:

```
data/kitaplar/
├── Topoloji_1/
│   └── topoloji_ders_notu.pdf
├── Kompleks_Analiz/
│   └── kompleks_analiz.pdf
└── Lineer_Cebir/
    └── lineer_cebir.pdf
```

Klasör adları `config/dersler.yaml` ile eşleşmeli.

### 2. PDF'leri İşle

```bash
python scripts/01_process_pdfs.py
```

Çıktı: `data/chunks.jsonl` (~10.000 satır, her biri bir bölüm parçası)

### 3. İndeks Oluştur

```bash
python scripts/02_build_index.py
```

İlk çalıştırmada embedding modeli indirilir (~90 MB, ücretsiz, API gerektirmez).

### 4. Soru Sor

```bash
# Kaynak paragrafları göster (ücretsiz, API gerektirmez)
python scripts/03_query.py "Cauchy teoremi nedir?"

# GPT-4o-mini ile doğal dil cevabı al (OpenAI API key gerekir)
python scripts/03_query.py "Cauchy teoremi nedir?" --llm

# Sohbet modu
python scripts/03_query.py --chat
python scripts/03_query.py --chat --llm
```

---

## Örnek Çıktı (retrieval modu)

```
Soru: Kompaktlık Topoloji'de nasıl tanımlanır?
============================================================
  3 sonuç bulundu
============================================================

[1] Topoloji I  ·  Sayfa 87  ·  TANIM  ·  benzerlik: 91%
--------------------------------------------------
Tanım 4.1. Bir X topolojik uzayının K ⊂ X alt kümesi kompakt
denir, eğer K'nın her açık örtüsünün sonlu bir alt örtüsü varsa...

[2] Reel Analiz  ·  Sayfa 124  ·  TEOREM  ·  benzerlik: 84%
--------------------------------------------------
Teorem 5.2 (Heine-Borel). R^n'de bir küme kompakttır ancak ve
ancak hem kapalı hem sınırlıdır...
```

---

## LLM Modu İçin API Key

```bash
# .env dosyası oluştur
echo "OPENAI_API_KEY=sk-..." > .env
```

GPT-4o-mini kullanır. ~10.000 soru için maliyet yaklaşık $2–5.

---

## Mevcut Dersler

| Yarıyıl | Dersler |
|---------|---------|
| 1–2 | Matematiksel Analiz I-II, Soyut Matematik, Analitik Geometri |
| 3–4 | Analiz III-IV, Lineer Cebir I, Diferansiyel Denklemler I-II, Sayısal Analiz I, Olasılık Teorisi |
| 5–6 | Kompleks Analiz, Topoloji I-II, Diferansiyel Geometri I-II, KTDD I-II |
| 7–8 | Reel Analiz, Fonksiyonel Analiz, Sayılar Teorisi |

---

## NotebookLM'den Farkı

| Özellik | NotebookLM | Bu Sistem |
|---------|-----------|-----------|
| Kaynak limiti | ~50 PDF | Sınırsız |
| Ders filtresi | Manuel | Otomatik |
| Türkçe soru → İngilizce kaynak | Zayıf | ✓ Embedding köprüsü |
| Çevrimdışı | Hayır | ✓ Evet |
| Metadata (ders/sayfa/tip) | Yok | ✓ Tam kontrol |
| Gizlilik | Google sunucusu | ✓ Yerel |

---

## Katkı

Bu proje Arş. Gör. Merve Dede tarafından Beykent Üniversitesi Matematik Kulübü semineri için hazırlanmıştır.
Katkı ve önerilere açıktır.

**İletişim:** mervedede@beykent.edu.tr
