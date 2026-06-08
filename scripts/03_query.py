#!/usr/bin/env python3
"""
Adım 3 — Soru Sor
==================
Bilgi tabanına doğal dil sorusu sorar.

Mod 1 — Sadece retrieval (API gerektirmez, ücretsiz):
    python scripts/03_query.py "Cauchy teoremi nedir?"

Mod 2 — LLM ile tam cevap (OpenAI API gerekir):
    python scripts/03_query.py "Cauchy teoremi nedir?" --llm

Mod 3 — İnteraktif sohbet modu:
    python scripts/03_query.py --chat
    python scripts/03_query.py --chat --llm
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT      = Path(__file__).resolve().parents[1]
INDEX_DIR = ROOT / "data" / "chroma_db"


def check_index():
    if not INDEX_DIR.exists() or not any(INDEX_DIR.iterdir()):
        print("[!] İndeks bulunamadı. Önce şunları çalıştırın:")
        print("    python scripts/01_process_pdfs.py")
        print("    python scripts/02_build_index.py\n")
        sys.exit(1)


def load_env():
    """Varsa .env dosyasından OPENAI_API_KEY yükle."""
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                import os
                os.environ.setdefault(key.strip(), val.strip())


def ask(question: str, use_llm: bool) -> None:
    from src.query_engine import retrieve, answer_with_llm, format_results

    hits = retrieve(question, persist_dir=INDEX_DIR)

    if use_llm:
        try:
            answer = answer_with_llm(question, hits)
            print(f"\n{'='*60}")
            print(f"Soru: {question}")
            print(f"{'='*60}")
            print(answer)
            if hits:
                print(f"\n{'─'*40}")
                print("Kaynaklar:")
                for h in hits[:4]:
                    print(f"  • {h['ders']} · Sayfa {h['sayfa']} · {h['tip']}")
        except EnvironmentError as e:
            print(f"\n[!] {e}")
            print("[→] LLM olmadan retrieval sonuçları:\n")
            print(format_results(hits))
    else:
        print(f"\nSoru: {question}")
        print(format_results(hits))


def chat_mode(use_llm: bool) -> None:
    print("\n" + "="*60)
    print("  Beykent Matematik RAG — Sohbet Modu")
    print("  Çıkmak için: 'q' veya 'quit'")
    print("="*60 + "\n")

    while True:
        try:
            question = input("Soru > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGüle güle!")
            break

        if not question:
            continue
        if question.lower() in ("q", "quit", "exit", "çık"):
            print("Güle güle!")
            break

        ask(question, use_llm)
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Matematik müfredatına soru sor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  python scripts/03_query.py "Cauchy teoremi nedir?"
  python scripts/03_query.py "Kompleks Analiz'de rezidü hesabı nasıl yapılır?" --llm
  python scripts/03_query.py "Limit tanımı hangi derslerde farklı?" --llm
  python scripts/03_query.py --chat
        """,
    )
    parser.add_argument("soru", nargs="?", help="Sorulacak soru")
    parser.add_argument("--llm",  action="store_true",
                        help="OpenAI GPT-4o-mini ile cevap üret (API key gerekir)")
    parser.add_argument("--chat", action="store_true",
                        help="İnteraktif sohbet modu")
    args = parser.parse_args()

    check_index()
    load_env()

    if args.chat:
        chat_mode(use_llm=args.llm)
    elif args.soru:
        ask(args.soru, use_llm=args.llm)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
