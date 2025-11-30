"""OCR engine abstraction."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import pytesseract
from pytesseract import Output
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
    """OCR result containing text, confidence and bounding boxes."""

    text: str
    confidence: Optional[float] = None
    boxes: Optional[List[Dict[str, object]]] = None


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
            return self._run_tesseract(image)
        if self.engine_name == "paddleocr" and self.engine:
            return self._run_paddleocr(image)
        if self.engine_name == "easyocr" and self.engine:
            return self._run_easyocr(image)
        raise ValueError(f"Unsupported or unavailable engine: {self.engine_name}")

    def _run_tesseract(self, image: Image.Image) -> OcrResult:
        """Run Tesseract and return text with bounding boxes and confidence."""

        data = pytesseract.image_to_data(image, lang="+".join(self.languages), output_type=Output.DICT)
        boxes: List[Dict[str, object]] = []
        confs: List[float] = []
        lines: Dict[str, List[str]] = {}

        for idx, text in enumerate(data.get("text", [])):
            stripped = text.strip()
            if not stripped:
                continue
            conf_value = float(data.get("conf", ["-1"])[idx])
            if conf_value >= 0:
                confs.append(conf_value)
            box = {
                "text": stripped,
                "bbox": {
                    "x": int(data.get("left", [0])[idx]),
                    "y": int(data.get("top", [0])[idx]),
                    "width": int(data.get("width", [0])[idx]),
                    "height": int(data.get("height", [0])[idx]),
                },
                "confidence": conf_value if conf_value >= 0 else None,
            }
            boxes.append(box)

            line_key = (
                data.get("page_num", [0])[idx],
                data.get("block_num", [0])[idx],
                data.get("par_num", [0])[idx],
                data.get("line_num", [0])[idx],
            )
            lines.setdefault(str(line_key), []).append(stripped)

        text_lines = [" ".join(words) for words in lines.values()]
        joined_text = "\n".join(text_lines)
        avg_conf = sum(confs) / len(confs) if confs else None

        return OcrResult(text=joined_text, confidence=avg_conf, boxes=boxes)

    def _run_paddleocr(self, image: Image.Image) -> OcrResult:
        """Run PaddleOCR with bounding boxes."""

        results = self.engine.ocr(image, cls=True)
        boxes: List[Dict[str, object]] = []
        texts: List[str] = []
        confs: List[float] = []

        for page in results or []:
            for line in page:
                quad = line[0]
                text, score = line[1]
                bbox = self._quad_to_bbox(quad)
                boxes.append({"text": text, "bbox": bbox, "confidence": float(score)})
                texts.append(text)
                confs.append(float(score))

        combined_text = "\n".join(texts)
        avg_conf = sum(confs) / len(confs) if confs else None
        return OcrResult(text=combined_text, confidence=avg_conf, boxes=boxes)

    def _run_easyocr(self, image: Image.Image) -> OcrResult:
        """Run EasyOCR with bounding boxes."""

        lines = self.engine.readtext(image)
        boxes: List[Dict[str, object]] = []
        texts: List[str] = []
        confs: List[float] = []

        for bbox_points, text, score in lines:
            bbox = self._quad_to_bbox(bbox_points)
            boxes.append({"text": text, "bbox": bbox, "confidence": float(score)})
            texts.append(text)
            confs.append(float(score))

        combined_text = "\n".join(texts)
        avg_conf = sum(confs) / len(confs) if confs else None
        return OcrResult(text=combined_text, confidence=avg_conf, boxes=boxes)

    @staticmethod
    def _quad_to_bbox(points) -> Dict[str, int]:
        """Convert quadrilateral coordinates to an (x, y, width, height) bounding box."""

        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        return {
            "x": int(min_x),
            "y": int(min_y),
            "width": int(max_x - min_x),
            "height": int(max_y - min_y),
        }
