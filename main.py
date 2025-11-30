"""Entry point for running the OCR app or CLI OCR."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from ocr_app.app import main as gui_main
from ocr_app.config import config
from ocr_app.core.ocr_service import gather_paths, run_ocr_on_path
from ocr_app.logging_utils import setup_logging


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OCR application")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("gui", help="Uruchom interfejs graficzny (domyślne)")

    ocr_parser = subparsers.add_parser("ocr", help="Uruchom OCR na plikach lub katalogach")
    ocr_parser.add_argument("paths", nargs="+", help="Ścieżki do plików lub katalogów")
    ocr_parser.add_argument(
        "--engine",
        choices=["tesseract", "paddleocr", "easyocr"],
        default=config.default_engine,
        help="Silnik OCR",
    )
    ocr_parser.add_argument(
        "--languages",
        nargs="+",
        default=config.default_languages,
        help="Lista języków (np. pol eng)",
    )
    ocr_parser.add_argument("--dpi", type=int, default=config.pdf_dpi, help="DPI dla PDF")
    ocr_parser.add_argument(
        "--recursive",
        action="store_true",
        help="Przeszukuj katalogi rekursywnie",
    )
    ocr_parser.add_argument(
        "--json-output",
        type=Path,
        help="Zapisz wynik w formacie JSON do wskazanego pliku",
    )
    ocr_parser.add_argument(
        "--tesseract-cmd",
        type=str,
        default=config.tesseract_cmd,
        help="Ścieżka do binarki tesseract (opcjonalnie)",
    )

    return parser.parse_args()


def _print_human_readable(path: Path, languages: List[str], engine: str, results) -> None:
    print(f"=== {path} ===")
    print(f"Silnik: {engine}; Języki: {', '.join(languages)}")
    for page in results:
        print(f"\n-- Strona {page.page_index} --")
        if page.confidence is not None:
            print(f"Pewność: {page.confidence:.2f}")
        print(page.text)


def _run_cli(args: argparse.Namespace) -> None:
    logger = setup_logging()
    input_paths = gather_paths([Path(p) for p in args.paths], recursive=args.recursive)
    if not input_paths:
        raise SystemExit("Nie znaleziono plików do przetworzenia")

    all_results = []
    for path in input_paths:
        pages = run_ocr_on_path(
            path,
            args.engine,
            args.languages,
            preprocess_options=config.preprocess_options,
            dpi=args.dpi,
            tesseract_cmd=args.tesseract_cmd,
        )
        _print_human_readable(path, args.languages, args.engine, pages)
        all_results.append(
            {
                "source": str(path),
                "engine": args.engine,
                "languages": args.languages,
                "pages": [
                    {
                        "page": page.page_index,
                        "text": page.text,
                        "confidence": page.confidence,
                        "boxes": page.boxes,
                    }
                    for page in pages
                ],
            }
        )

    if args.json_output:
        args.json_output.write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Zapisano wynik do %s", args.json_output)


def main() -> None:
    args = _parse_args()
    if args.command == "ocr":
        _run_cli(args)
    else:
        gui_main()


if __name__ == "__main__":
    main()
