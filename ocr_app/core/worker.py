"""Task worker to process a single page."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image

from .image_preprocess import preprocess_image
from .ocr_engine import OcrEngine, OcrResult


@dataclass
class PageTask:
    """Metadata for a single OCR task."""

    source_file: Path
    page_index: int
    engine_name: str
    languages: List[str]
    preprocess_options: Dict[str, bool]
    tesseract_cmd: str = ""


def process_page(image: Image.Image, task: PageTask, preprocessed: Optional[Image.Image] = None) -> OcrResult:
    """Process one page: preprocess (if needed) then run OCR."""
    processed = preprocessed or preprocess_image(image, task.preprocess_options)[0]
    engine = OcrEngine(task.engine_name, task.languages, task.tesseract_cmd)
    return engine.run(processed)
