"""Global configuration for the OCR application."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class OCRConfig:
    """Configuration options for OCR processing and application defaults."""

    tesseract_cmd: str = ""
    default_engine: str = "tesseract"
    available_languages: List[str] = field(default_factory=lambda: ["pol", "eng"])
    default_languages: List[str] = field(default_factory=lambda: ["pol", "eng"])
    pdf_dpi: int = 300
    max_workers: int = 4
    temp_dir: Path = Path("./tmp")
    log_file: Path = Path("./ocr_app.log")
    metrics_file: Path = Path("./metrics/ocr_metrics.csv")
    preprocess_options: dict = field(
        default_factory=lambda: {
            "grayscale": True,
            "denoise": True,
            "threshold": True,
            "deskew": True,
            "scale_up": True,
            "remove_background": False,
        }
    )

    def ensure_dirs(self) -> None:
        """Create required directories if they do not exist."""
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)


config = OCRConfig()
