"""Global configuration for the OCR application."""
from __future__ import annotations

from dataclasses import dataclass, field, is_dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml


def _update_dataclass(instance, data: Dict) -> None:
    """Recursively update a dataclass instance with values from a dict."""

    for key, value in data.items():
        if not hasattr(instance, key):
            continue
        current_value = getattr(instance, key)
        if is_dataclass(current_value) and isinstance(value, dict):
            _update_dataclass(current_value, value)
        else:
            setattr(instance, key, value)


@dataclass
class PaddleModelPaths:
    """File locations for PaddleOCR models."""

    det_model_dir: Optional[Path] = None
    rec_model_dir: Optional[Path] = None
    cls_model_dir: Optional[Path] = None

    def as_kwargs(self) -> Dict[str, str]:
        """Convert provided paths to PaddleOCR keyword arguments."""

        mapping = {
            "det_model_dir": self.det_model_dir,
            "rec_model_dir": self.rec_model_dir,
            "cls_model_dir": self.cls_model_dir,
        }
        return {key: str(val) for key, val in mapping.items() if val}

    def missing_paths(self) -> List[Path]:
        """Return a list of model paths that do not yet exist."""

        return [path for path in (self.det_model_dir, self.rec_model_dir, self.cls_model_dir) if path and not path.exists()]


@dataclass
class EasyOcrModelPath:
    """Storage path for EasyOCR models."""

    model_dir: Optional[Path] = None

    def missing_paths(self) -> List[Path]:
        """Return a list of EasyOCR model directories that are missing."""

        return [self.model_dir] if self.model_dir and not self.model_dir.exists() else []


@dataclass
class ModelConfig:
    """Aggregated model locations and behaviour when models are missing."""

    tesseract_cmd: str = ""
    paddleocr: PaddleModelPaths = field(default_factory=PaddleModelPaths)
    easyocr: EasyOcrModelPath = field(default_factory=EasyOcrModelPath)
    auto_download_missing: bool = True

    def missing_models(self) -> List[str]:
        """Return human-readable descriptions of missing model locations."""

        missing = []
        for path in self.paddleocr.missing_paths():
            missing.append(f"PaddleOCR model: {path}")
        for path in self.easyocr.missing_paths():
            missing.append(f"EasyOCR models: {path}")
        return missing

    def manual_instruction(self) -> str:
        """Return installation guidance for users."""

        return (
            "Modele nie są dostępne. Pobierz je ręcznie lub usuń ścieżki z config.yml, "
            "aby pozwolić bibliotekom na automatyczne pobieranie. Dla PaddleOCR "
            "użyj `paddleocr --det_model_dir <ścieżka> --rec_model_dir <ścieżka> --cls_model_dir <ścieżka>`, "
            "dla EasyOCR skopiuj modele do katalogu `model_dir` lub włącz auto_download_missing."
        )


@dataclass
class OCRConfig:
    """Configuration options for OCR processing and application defaults."""

    models: ModelConfig = field(default_factory=ModelConfig)
    available_languages: List[str] = field(default_factory=lambda: ["pol", "eng"])
    default_languages: List[str] = field(default_factory=lambda: ["pol", "eng"])
    pdf_dpi: int = 300
    default_engine: str = "tesseract"
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

    def prepare_models(self) -> None:
        """Handle missing models by preparing directories or warning users."""

        import logging

        logger = logging.getLogger(__name__)
        missing = self.models.missing_models()

        if not missing:
            return

        if self.models.auto_download_missing:
            for path in self.models.easyocr.missing_paths():
                path.mkdir(parents=True, exist_ok=True)
                logger.info(
                    "Brak modeli EasyOCR pod %s. Utworzono katalog – biblioteka pobierze modele automatycznie.",
                    path,
                )
            if self.models.paddleocr.missing_paths():
                logger.info(
                    "Brak modeli PaddleOCR: %s. Ścieżki zostaną pominięte, a biblioteka pobierze modele domyślne.",
                    ", ".join(str(p) for p in self.models.paddleocr.missing_paths()),
                )
                self.models.paddleocr = PaddleModelPaths()
        else:
            logger.warning(self.models.manual_instruction())
            for item in missing:
                logger.warning(" - %s", item)


def load_config(config_path: Optional[Path | str] = None) -> OCRConfig:
    """Load configuration from YAML, falling back to defaults when unavailable."""

    config = OCRConfig()
    path = Path(config_path) if config_path else Path(__file__).with_name("config.yml")
    if path.exists():
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        _update_dataclass(config, _normalize_schema(loaded))
    config.ensure_dirs()
    config.prepare_models()
    return config


def _normalize_schema(raw: Dict) -> Dict:
    """Map YAML keys to dataclass fields with backward compatibility."""

    normalized = dict(raw)
    models = normalized.get("models", {}) if isinstance(normalized.get("models", {}), dict) else {}
    paddle_models = models.get("paddleocr", {}) if isinstance(models.get("paddleocr", {}), dict) else {}
    easyocr_model_dir = models.get("easyocr", {}) if isinstance(models.get("easyocr", {}), dict) else {}
    if paddle_models:
        for key in ("det_model_dir", "rec_model_dir", "cls_model_dir"):
            if key in paddle_models and paddle_models[key]:
                paddle_models[key] = Path(paddle_models[key])
        models["paddleocr"] = paddle_models
    if isinstance(easyocr_model_dir, dict) and easyocr_model_dir.get("model_dir"):
        easyocr_model_dir["model_dir"] = Path(easyocr_model_dir["model_dir"])
        models["easyocr"] = easyocr_model_dir
    if models:
        normalized["models"] = models
    if "pdf" in raw and isinstance(raw["pdf"], dict):
        normalized["pdf_dpi"] = raw["pdf"].get("dpi", normalized.get("pdf_dpi", 300))
    if "app" in raw and isinstance(raw["app"], dict):
        normalized.setdefault("default_engine", raw["app"].get("default_engine", "tesseract"))
        normalized.setdefault("max_workers", raw["app"].get("max_workers", 4))
        normalized.setdefault("temp_dir", Path(raw["app"].get("temp_dir", "./tmp")))
        normalized.setdefault("log_file", Path(raw["app"].get("log_file", "./ocr_app.log")))
    if "languages" in raw and isinstance(raw["languages"], dict):
        normalized.setdefault("available_languages", raw["languages"].get("available", ["pol", "eng"]))
        normalized.setdefault("default_languages", raw["languages"].get("default", ["pol", "eng"]))
    if "preprocess" in raw and isinstance(raw["preprocess"], dict):
        normalized.setdefault("preprocess_options", raw["preprocess"])
    return normalized


config = load_config()
