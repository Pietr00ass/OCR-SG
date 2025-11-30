"""Text region detection helpers."""
from __future__ import annotations

import logging
from typing import Iterable, List, Sequence, Tuple

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

BoundingBox = Tuple[int, int, int, int]


def _safe_import_easyocr():
    try:  # pragma: no cover - optional dependency
        import easyocr
    except (ImportError, OSError) as exc:  # pragma: no cover - optional dependency
        logger.info("EasyOCR unavailable for detection: %s", exc)
        return None
    return easyocr


easyocr = _safe_import_easyocr()


def _to_array(image: Image.Image) -> np.ndarray:
    return np.array(image)


def detect_text_regions(
    image: Image.Image,
    detector: str = "easyocr",
    languages: Sequence[str] | None = None,
    min_area: int = 300,
) -> List[BoundingBox]:
    """Detect text regions using EasyOCR detector when available.

    Falls back to contour-based detection when the deep-learning detector is not
    present, ensuring the pipeline still returns reasonable bounding boxes.
    """

    if detector.lower() == "easyocr" and easyocr:
        reader = easyocr.Reader(list(languages or ["en"]))
        boxes, _ = reader.detect(_to_array(image), min_size=8)
        flattened = []
        for box_group in boxes:
            for box in box_group:
                xs = [pt[0] for pt in box]
                ys = [pt[1] for pt in box]
                flattened.append((int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))))
        return _sort_boxes(flattened)

    return _detect_via_contours(image, min_area=min_area)


def _detect_via_contours(image: Image.Image, min_area: int = 300) -> List[BoundingBox]:
    """Simple contour-based text region proposal using morphology."""

    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 3))
    morphed = cv2.dilate(binary, kernel, iterations=2)
    contours, _ = cv2.findContours(morphed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes: List[BoundingBox] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w * h < min_area:
            continue
        boxes.append((x, y, x + w, y + h))
    return _sort_boxes(boxes)


def _sort_boxes(boxes: Iterable[BoundingBox]) -> List[BoundingBox]:
    return sorted(boxes, key=lambda box: (box[1], box[0]))


__all__: Iterable[str] = ["BoundingBox", "detect_text_regions"]
