"""Command-line interface for running OCR in batch mode."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List, Sequence

from PIL import Image

from .config import OCRConfig, load_config
from .core.exporter import export_docx, export_txt
from .core.image_preprocess import preprocess_image
from .core.ocr_engine import OcrEngine
from .core.pdf_loader import load_pdf_pages


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CLI do wsadowego uruchamiania OCR")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Ścieżka do config.yml. Domyślnie używa pliku z katalogu ocr_app.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common_args(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument(
            "--languages",
            nargs="+",
            help="Kody języków (np. pol eng). Domyślnie wartości z config.yml.",
        )
        subparser.add_argument(
            "--engine",
            choices=["tesseract", "paddleocr", "easyocr"],
            help="Silnik OCR. Domyślnie zgodnie z config.yml.",
        )
        subparser.add_argument(
            "--output-dir",
            type=Path,
            default=Path("output"),
            help="Katalog zapisu wyników (domyślnie ./output).",
        )
        subparser.add_argument(
            "--format",
            choices=["txt", "docx"],
            default="txt",
            help="Format wyjściowy (txt lub docx).",
        )

    pdf_parser = subparsers.add_parser("pdf", help="Konwersja PDF do tekstu")
    pdf_parser.add_argument("pdf", type=Path, help="Ścieżka do pliku PDF")
    pdf_parser.add_argument(
        "--dpi",
        type=int,
        help="DPI renderowania stron PDF (domyślnie z config.yml).",
    )
    add_common_args(pdf_parser)

    img_parser = subparsers.add_parser("images", help="Konwersja obrazów do tekstu")
    img_parser.add_argument("images", nargs="+", type=Path, help="Ścieżki do obrazów")
    add_common_args(img_parser)

    return parser


def _prepare_engine(config: OCRConfig, engine_name: str | None, languages: Sequence[str] | None) -> OcrEngine:
    selected_engine = (engine_name or config.default_engine).lower()
    selected_languages = list(languages or config.default_languages)
    return OcrEngine(
        engine_name=selected_engine,
        languages=selected_languages,
        tesseract_cmd=config.models.tesseract_cmd,
        model_config=config.models,
    )


def _export(pages: List[str], output_dir: Path, base_name: str, file_format: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    extension = file_format.lower()
    output_path = output_dir / f"{base_name}.{extension}"
    if extension == "docx":
        export_docx(output_path, pages)
    else:
        export_txt(output_path, pages)
    return output_path


def _run_on_images(images: Iterable[Image.Image], engine: OcrEngine, preprocess_options: dict) -> List[str]:
    pages: List[str] = []
    for image in images:
        processed, _ = preprocess_image(image, preprocess_options)
        result = engine.run(processed)
        pages.append(result.text)
    return pages


def handle_pdf(args: argparse.Namespace, config: OCRConfig) -> Path:
    engine = _prepare_engine(config, args.engine, args.languages)
    dpi = args.dpi or config.pdf_dpi
    pages = [
        image
        for _, image in load_pdf_pages(args.pdf, dpi=dpi)
    ]
    texts = _run_on_images(pages, engine, config.preprocess_options)
    return _export(texts, args.output_dir, args.pdf.stem, args.format)


def handle_images(args: argparse.Namespace, config: OCRConfig) -> Path:
    engine = _prepare_engine(config, args.engine, args.languages)
    loaded_images = [Image.open(path).convert("RGB") for path in args.images]
    texts = _run_on_images(loaded_images, engine, config.preprocess_options)
    base_name = "batch" if len(args.images) > 1 else args.images[0].stem
    return _export(texts, args.output_dir, base_name, args.format)


def main(argv: Sequence[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    config = load_config(args.config)

    if args.command == "pdf":
        output_path = handle_pdf(args, config)
    elif args.command == "images":
        output_path = handle_images(args, config)
    else:  # pragma: no cover - safety net
        parser.error("Nieznana komenda")
        return

    print(f"Zapisano wynik do: {output_path}")


if __name__ == "__main__":  # pragma: no cover
    main()
