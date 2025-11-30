"""Image preprocessing utilities using OpenCV."""
from __future__ import annotations

from typing import Dict, Tuple

import cv2
import numpy as np
from PIL import Image


def pil_to_cv(image: Image.Image) -> np.ndarray:
    """Convert a PIL Image to an OpenCV-compatible array."""
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


def cv_to_pil(image: np.ndarray) -> Image.Image:
    """Convert an OpenCV image to PIL."""
    return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))


def deskew(image: np.ndarray) -> np.ndarray:
    """Estimate skew angle and rotate image to correct orientation."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    coords = np.column_stack(np.where(gray > 0))
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def preprocess_image(pil_image: Image.Image, options: Dict[str, bool]) -> Tuple[Image.Image, Dict[str, float]]:
    """Run the preprocessing pipeline on a PIL image."""
    cv_img = pil_to_cv(pil_image)
    metrics: Dict[str, float] = {}

    if options.get("grayscale", True):
        cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        cv_img = cv2.cvtColor(cv_img, cv2.COLOR_GRAY2BGR)

    if options.get("denoise", True):
        cv_img = cv2.medianBlur(cv_img, 3)

    if options.get("threshold", True):
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        _, bin_img = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        cv_img = cv2.cvtColor(bin_img, cv2.COLOR_GRAY2BGR)

    if options.get("scale_up", False):
        cv_img = cv2.resize(cv_img, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)

    if options.get("deskew", False):
        try:
            cv_img = deskew(cv_img)
        except Exception:
            pass

    if options.get("remove_background", False):
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        bg = cv2.medianBlur(gray, 21)
        diff = 255 - cv2.absdiff(gray, bg)
        norm = cv2.normalize(diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
        cv_img = cv2.cvtColor(norm, cv2.COLOR_GRAY2BGR)

    return cv_to_pil(cv_img), metrics
