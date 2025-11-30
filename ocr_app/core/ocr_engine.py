"""OCR engine abstraction."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import pytesseract
from PIL import Image

from ..config import ModelConfig

logger = logging.getLogger(__name__)


def _safe_import_paddleocr():
    try:
        from paddleocr import PaddleOCR
    except ImportError:  # pragma: no cover - optional dependency
        logger.info("PaddleOCR not installed; skipping import.")
        return None
    except OSError as exc:  # pragma: no cover - optional dependency
        logger.warning(
            "PaddleOCR failed to load (likely missing CPU build or VC++ runtime). %s",
            exc,
        )
        if "c10.dll" in str(exc).lower():
            logger.warning(
                "Detected c10.dll load issue. Reinstall CPU PyTorch/EasyOCR/PaddleOCR: "
                "pip uninstall -y torch torchvision torchaudio paddlepaddle paddleocr easyocr && "
                "pip install --no-cache-dir -r requirements.txt"
            )
        return None
    return PaddleOCR


PaddleOCR = _safe_import_paddleocr()


def _safe_import_easyocr():
    try:
        import easyocr
    except ImportError:  # pragma: no cover - optional dependency
        logger.info("EasyOCR not installed; skipping import.")
        return None
    except OSError as exc:  # pragma: no cover - optional dependency
        logger.warning("EasyOCR failed to load: %s", exc)
        if "c10.dll" in str(exc).lower():
            logger.warning(
                "Detected c10.dll load issue. Reinstall CPU PyTorch/EasyOCR/PaddleOCR: "
                "pip uninstall -y torch torchvision torchaudio paddlepaddle paddleocr easyocr && "
                "pip install --no-cache-dir -r requirements.txt"
            )
        return None
    return easyocr


easyocr = _safe_import_easyocr()


@dataclass
class OcrResult:
    """OCR result containing text and optional metadata."""

    text: str
    confidence: Optional[float] = None


class OcrEngine:
    """Selectable OCR engine facade."""

    def __init__(
        self,
        engine_name: str,
        languages: List[str],
        tesseract_cmd: str = "",
        model_config: Optional[ModelConfig] = None,
    ) -> None:
        self.engine_name = engine_name.lower()
        self.languages = languages
        config = model_config or ModelConfig()
        tesseract_path = tesseract_cmd or config.tesseract_cmd
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

        if self.engine_name == "paddleocr" and PaddleOCR:
            paddle_kwargs: Dict[str, str] = {}
            missing_paths = config.paddleocr.missing_paths()
            if missing_paths and not config.auto_download_missing:
                message = (
                    "Brak modeli PaddleOCR: "
                    + ", ".join(str(path) for path in missing_paths)
                    + ". Pobierz je zgodnie z instrukcjami w config.yml."
                )
                raise SystemExit(message)
            if not missing_paths:
                paddle_kwargs = config.paddleocr.as_kwargs()
            else:
                logger.info(
                    "Brak modeli PaddleOCR (%s). Używam domyślnego mechanizmu pobierania biblioteki.",
                    ", ".join(str(p) for p in missing_paths),
                )
            self.engine = PaddleOCR(lang="+".join(languages), **paddle_kwargs)
        elif self.engine_name == "paddleocr" and not PaddleOCR:
            logger.warning(
                "PaddleOCR unavailable. Ensure CPU build is installed and Visual C++ runtimes are present."
            )
            self.engine = None
        elif self.engine_name == "easyocr" and easyocr:
            missing_paths = config.easyocr.missing_paths()
            if missing_paths and not config.auto_download_missing:
                message = (
                    "Brak modeli EasyOCR w: "
                    + ", ".join(str(path) for path in missing_paths)
                    + ". Pobierz je ręcznie lub włącz auto_download_missing."
                )
                raise SystemExit(message)
            model_dir = config.easyocr.model_dir
            if model_dir:
                model_dir.mkdir(parents=True, exist_ok=True)
            self.engine = easyocr.Reader(
                languages,
                model_storage_directory=str(model_dir) if model_dir else None,
                download_enabled=config.auto_download_missing,
            )
        elif self.engine_name == "easyocr" and not easyocr:
            logger.warning("EasyOCR unavailable. Install optional dependency 'easyocr'.")
            self.engine = None
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
