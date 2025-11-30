"""Shared OCR helpers for API and CLI entrypoints."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterable, List, Optional, Sequence

from PIL import Image

from ..config import config
from ..logging_utils import setup_logging
from . import pdf_loader
from .image_preprocess import preprocess_image
from .worker import PageTask, process_page


logger = logging.getLogger(__name__)
setup_logging()


SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
SUPPORTED_DOC_SUFFIXES = SUPPORTED_IMAGE_SUFFIXES | {".pdf"}


@dataclass
class PageOcrResult:
    """Structured OCR output for a single page."""

    page_index: int
    text: str
    confidence: Optional[float]
    boxes: List[dict]


def gather_paths(inputs: Sequence[Path], recursive: bool = False) -> List[Path]:
    """Collect supported files from a list of input paths."""

    collected: List[Path] = []
    for path in inputs:
        if not path.exists():
            logger.warning("Ścieżka nie istnieje: %s", path)
            continue
        if path.is_dir():
            if recursive:
                for candidate in path.rglob("*"):
                    if candidate.suffix.lower() in SUPPORTED_DOC_SUFFIXES:
                        collected.append(candidate)
            else:
                for candidate in path.iterdir():
                    if candidate.suffix.lower() in SUPPORTED_DOC_SUFFIXES:
                        collected.append(candidate)
        elif path.suffix.lower() in SUPPORTED_DOC_SUFFIXES:
            collected.append(path)
        else:
            logger.warning("Pomijam nieobsługiwany plik: %s", path)
    return collected


def _iterate_images(path: Path, dpi: int) -> Iterable[tuple[int, Image.Image]]:
    if path.suffix.lower() == ".pdf":
        yield from pdf_loader.load_pdf_pages(path, dpi=dpi)
    else:
        yield 0, Image.open(path)


def run_ocr_on_path(
    path: Path,
    engine_name: str,
    languages: List[str],
    preprocess_options: Optional[dict] = None,
    dpi: int = 300,
    tesseract_cmd: str = "",
) -> List[PageOcrResult]:
    """Process a file (image or PDF) and return per-page OCR results."""

    preprocess_opts = preprocess_options or config.preprocess_options
    page_results: List[PageOcrResult] = []

    for page_index, image in _iterate_images(path, dpi=dpi):
        task = PageTask(
            source_file=path,
            page_index=page_index,
            engine_name=engine_name,
            languages=languages,
            preprocess_options=preprocess_opts,
            tesseract_cmd=tesseract_cmd,
        )
        processed, _ = preprocess_image(image, preprocess_opts)
        result = process_page(image, task, preprocessed=processed)
        page_results.append(
            PageOcrResult(
                page_index=page_index,
                text=result.text,
                confidence=result.confidence,
                boxes=result.boxes or [],
            )
        )

    return page_results


def run_ocr_on_bytes(
    payload: bytes,
    filename: str,
    engine_name: str,
    languages: List[str],
    preprocess_options: Optional[dict] = None,
    dpi: int = 300,
    tesseract_cmd: str = "",
) -> List[PageOcrResult]:
    """Handle OCR for uploaded content (image or PDF)."""

    suffix = Path(filename).suffix.lower()
    preprocess_opts = preprocess_options or config.preprocess_options

    if suffix == ".pdf":
        with NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
            tmp.write(payload)
            tmp.flush()
            return run_ocr_on_path(Path(tmp.name), engine_name, languages, preprocess_opts, dpi, tesseract_cmd)

    image = Image.open(BytesIO(payload))
    task = PageTask(
        source_file=Path(filename or "upload"),
        page_index=0,
        engine_name=engine_name,
        languages=languages,
        preprocess_options=preprocess_opts,
        tesseract_cmd=tesseract_cmd,
    )
    processed, _ = preprocess_image(image, preprocess_opts)
    result = process_page(image, task, preprocessed=processed)
    return [
        PageOcrResult(
            page_index=0,
            text=result.text,
            confidence=result.confidence,
            boxes=result.boxes or [],
        )
    ]

