"""OCR engine abstraction."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pytesseract
from PIL import Image

try:
    from paddleocr import PaddleOCR
except ImportError:  # pragma: no cover - optional dependency
    PaddleOCR = None

try:
    import easyocr
except ImportError:  # pragma: no cover - optional dependency
    easyocr = None


@dataclass
class OcrResult:
    """OCR result containing text and optional metadata."""

    text: str
    confidence: Optional[float] = None


class OcrEngine:
    """Selectable OCR engine facade."""

    def __init__(self, engine_name: str, languages: List[str], tesseract_cmd: str = "") -> None:
        self.engine_name = engine_name.lower()
        self.languages = languages
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

        if self.engine_name == "paddleocr" and PaddleOCR:
            self.engine = PaddleOCR(lang="+".join(languages))
        elif self.engine_name == "easyocr" and easyocr:
            self.engine = easyocr.Reader(languages)
        else:
            self.engine = None

    def run(self, image: Image.Image) -> OcrResult:
        """Execute OCR using the configured engine."""
        if self.engine_name == "tesseract":
            text = pytesseract.image_to_string(image, lang="+".join(self.languages))
            return OcrResult(text=text)
        if self.engine_name == "paddleocr" and self.engine:
            results = self.engine.ocr(image, cls=True)
            text = "\n".join([" ".join([line[1][0] for line in page]) for page in results])
            return OcrResult(text=text)
        if self.engine_name == "easyocr" and self.engine:
            lines = self.engine.readtext(image)
            text = "\n".join([line[1] for line in lines])
            return OcrResult(text=text)
        raise ValueError(f"Unsupported or unavailable engine: {self.engine_name}")
