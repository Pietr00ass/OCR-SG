"""Preprocessing helpers for OCR-ready images."""
from __future__ import annotations

from typing import Iterable, Sequence, Tuple

import cv2
import numpy as np
from PIL import Image

BoundingBox = Tuple[int, int, int, int]


def _to_bgr(image: Image.Image) -> np.ndarray:
    """Convert PIL image to OpenCV BGR array."""
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


def _to_pil(image: np.ndarray) -> Image.Image:
    """Convert OpenCV BGR array to PIL image."""
    return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))


def denoise(image: Image.Image, kernel_size: int = 3) -> Image.Image:
    """Remove small noise artifacts using median blur."""
    bgr = _to_bgr(image)
    cleaned = cv2.medianBlur(bgr, kernel_size)
    return _to_pil(cleaned)


def binarize(image: Image.Image) -> Image.Image:
    """Convert to binary image using Otsu thresholding."""
    bgr = _to_bgr(image)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    binary_bgr = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
    return _to_pil(binary_bgr)


def deskew(image: Image.Image) -> Image.Image:
    """Estimate and correct image rotation based on foreground content."""
    bgr = _to_bgr(image)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    coords = np.column_stack(np.where(gray > 0))
    if coords.size == 0:
        return image
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = bgr.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(bgr, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return _to_pil(rotated)


def crop(image: Image.Image, bbox: BoundingBox) -> Image.Image:
    """Crop image to the given bounding box (x1, y1, x2, y2)."""
    x1, y1, x2, y2 = bbox
    return image.crop((x1, y1, x2, y2))


def apply_preprocessing(image: Image.Image, steps: Sequence[str] | None = None) -> Image.Image:
    """Run a predefined set of preprocessing steps in order."""

    pipeline = list(steps) if steps is not None else ["denoise", "binarize", "deskew"]
    current = image
    for step in pipeline:
        if step == "denoise":
            current = denoise(current)
        elif step == "binarize":
            current = binarize(current)
        elif step == "deskew":
            current = deskew(current)
        elif step == "crop":
            # Crop needs explicit bounding boxes; skip in generic pipeline.
            continue
    return current


__all__: Iterable[str] = [
    "BoundingBox",
    "apply_preprocessing",
    "binarize",
    "crop",
    "denoise",
    "deskew",
]
