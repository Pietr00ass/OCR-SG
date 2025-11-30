"""Entry point for running the OCR app or CLI pipeline."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from PIL import Image

from ocr_app import detection, preprocess
from ocr_app.core.ocr_engine import OcrEngine


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OCR pipeline (GUI or CLI)")
    parser.add_argument("--image", type=Path, help="Ścieżka do pliku graficznego dla trybu CLI")
    parser.add_argument(
        "--engine",
        default="tesseract",
        choices=["tesseract", "paddleocr", "easyocr"],
        help="Silnik OCR do użycia w trybie CLI",
    )
    parser.add_argument(
        "--languages",
        default="pol,eng",
        help="Lista języków rozdzielona przecinkami dla trybu CLI",
    )
    parser.add_argument(
        "--detector",
        default="easyocr",
        choices=["easyocr", "contours"],
        help="Detektor regionów tekstu w trybie CLI",
    )
    return parser.parse_args()


def _run_cli_pipeline(image_path: Path, engine_name: str, languages: List[str], detector: str) -> str:
    """Minimalny pipeline: preprocess → detekcja → rozpoznanie."""

    image = Image.open(image_path)
    processed = preprocess.apply_preprocessing(image)
    boxes = detection.detect_text_regions(
        processed, detector=detector, languages=languages if languages else None
    )

    engine = OcrEngine(engine_name, languages)
    results: List[str] = []

    if boxes:
        for bbox in boxes:
            region = preprocess.crop(processed, bbox)
            results.append(engine.run(region).text.strip())
    else:
        results.append(engine.run(processed).text.strip())

    combined = "\n".join(filter(None, results))
    print(combined)
    return combined


def main() -> None:
    args = _parse_args()
    if args.image:
        _run_cli_pipeline(
            image_path=args.image,
            engine_name=args.engine,
            languages=[lang.strip() for lang in args.languages.split(",") if lang.strip()],
            detector=args.detector,
        )
    else:
        from ocr_app.app import main as gui_main

        gui_main()


if __name__ == "__main__":
    main()
