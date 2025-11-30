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
        _update_dataclass(config, _normalize_schema(loaded, source=str(path)))
    config.ensure_dirs()
    config.prepare_models()
    return config


def _normalize_schema(raw: Dict, *, source: str) -> Dict:
    """Map YAML keys to dataclass fields with validation and clear errors."""

    if not isinstance(raw, dict):
        raise ValueError(f"Plik {source} musi zawierać obiekt mapy (YAML dict) na poziomie root.")

    errors: List[str] = []
    normalized: Dict = {}

    def _validate_dict(value, section: str) -> Optional[Dict]:
        if not isinstance(value, dict):
            errors.append(f"Sekcja {section} w {source} musi być słownikiem.")
            return None
        return value

    def _validate_path(value, section: str) -> Optional[Path]:
        if value is None:
            return None
        if isinstance(value, (str, Path)):
            return Path(value)
        errors.append(f"Pole {section} w {source} musi być ścieżką (string lub Path).")
        return None

    allowed_root = {"models", "languages", "pdf", "app", "preprocess"}
    for key in raw:
        if key not in allowed_root:
            errors.append(f"Nieznany klucz na poziomie root: {key} (plik {source}).")

    # Models
    models_raw = raw.get("models", {})
    models_normalized: Dict = {}
    models_dict = _validate_dict(models_raw, "models") if models_raw else {}
    if models_dict is not None:
        allowed_models = {"tesseract_cmd", "paddleocr", "easyocr", "auto_download_missing"}
        for key in models_dict:
            if key not in allowed_models:
                errors.append(f"Nieznany klucz models.{key} w {source}.")

        auto_download = models_dict.get("auto_download_missing", True)
        if "auto_download_missing" in models_dict:
            if isinstance(auto_download, bool):
                models_normalized["auto_download_missing"] = auto_download
            else:
                errors.append("models.auto_download_missing musi być wartością logiczną (true/false).")
                auto_download = True

        if "tesseract_cmd" in models_dict:
            if isinstance(models_dict["tesseract_cmd"], str):
                models_normalized["tesseract_cmd"] = models_dict["tesseract_cmd"]
            else:
                errors.append("models.tesseract_cmd musi być tekstem.")

        if "paddleocr" in models_dict:
            paddle = _validate_dict(models_dict.get("paddleocr"), "models.paddleocr")
            if paddle is not None:
                allowed_paddle = {"det_model_dir", "rec_model_dir", "cls_model_dir"}
                for key in paddle:
                    if key not in allowed_paddle:
                        errors.append(f"Nieznany klucz models.paddleocr.{key} w {source}.")
                paddle_normalized = {}
                for key in allowed_paddle:
                    if key in paddle:
                        path_value = _validate_path(paddle[key], f"models.paddleocr.{key}")
                        if path_value:
                            if not path_value.exists() and auto_download is False:
                                errors.append(
                                    f"Ścieżka {key} w sekcji models.paddleocr nie istnieje: {path_value}"
                                )
                            paddle_normalized[key] = path_value
                if paddle_normalized:
                    models_normalized["paddleocr"] = paddle_normalized

        if "easyocr" in models_dict:
            easyocr = _validate_dict(models_dict.get("easyocr"), "models.easyocr")
            if easyocr is not None:
                allowed_easyocr = {"model_dir"}
                for key in easyocr:
                    if key not in allowed_easyocr:
                        errors.append(f"Nieznany klucz models.easyocr.{key} w {source}.")
                if "model_dir" in easyocr:
                    path_value = _validate_path(easyocr.get("model_dir"), "models.easyocr.model_dir")
                    if path_value:
                        if not path_value.exists() and auto_download is False:
                            errors.append(
                                f"Ścieżka models.easyocr.model_dir nie istnieje: {path_value}"
                            )
                        models_normalized.setdefault("easyocr", {})["model_dir"] = path_value

    if models_normalized:
        normalized["models"] = models_normalized

    # Languages
    if "languages" in raw:
        languages = _validate_dict(raw["languages"], "languages")
        if languages is not None:
            allowed_lang_keys = {"available", "default"}
            for key in languages:
                if key not in allowed_lang_keys:
                    errors.append(f"Nieznany klucz languages.{key} w {source}.")
            for key, target in (("available", "available_languages"), ("default", "default_languages")):
                if key in languages:
                    values = languages[key]
                    if not isinstance(values, list) or not all(isinstance(val, str) for val in values):
                        errors.append(f"languages.{key} musi być listą stringów.")
                    else:
                        normalized[target] = values

    # PDF
    if "pdf" in raw:
        pdf = _validate_dict(raw["pdf"], "pdf")
        if pdf is not None:
            for key in pdf:
                if key != "dpi":
                    errors.append(f"Nieznany klucz pdf.{key} w {source}.")
            if "dpi" in pdf:
                dpi = pdf["dpi"]
                if not isinstance(dpi, int):
                    errors.append("pdf.dpi musi być liczbą całkowitą.")
                elif dpi <= 0:
                    errors.append("pdf.dpi musi być dodatnią liczbą całkowitą.")
                else:
                    normalized["pdf_dpi"] = dpi

    # App
    if "app" in raw:
        app = _validate_dict(raw["app"], "app")
        if app is not None:
            allowed_app = {"default_engine", "max_workers", "temp_dir", "log_file"}
            for key in app:
                if key not in allowed_app:
                    errors.append(f"Nieznany klucz app.{key} w {source}.")
            if "default_engine" in app:
                if isinstance(app["default_engine"], str):
                    normalized.setdefault("default_engine", app["default_engine"])
                else:
                    errors.append("app.default_engine musi być tekstem.")
            if "max_workers" in app:
                max_workers = app["max_workers"]
                if not isinstance(max_workers, int):
                    errors.append("app.max_workers musi być liczbą całkowitą.")
                elif max_workers <= 0:
                    errors.append("app.max_workers musi być dodatnią liczbą całkowitą.")
                else:
                    normalized.setdefault("max_workers", max_workers)
            if "temp_dir" in app:
                path_value = _validate_path(app["temp_dir"], "app.temp_dir")
                if path_value is not None:
                    normalized.setdefault("temp_dir", path_value)
            if "log_file" in app:
                path_value = _validate_path(app["log_file"], "app.log_file")
                if path_value is not None:
                    normalized.setdefault("log_file", path_value)

    # Preprocess
    if "preprocess" in raw:
        preprocess = _validate_dict(raw["preprocess"], "preprocess")
        if preprocess is not None:
            allowed_preprocess = {
                "grayscale",
                "denoise",
                "threshold",
                "deskew",
                "scale_up",
                "remove_background",
            }
            for key in preprocess:
                if key not in allowed_preprocess:
                    errors.append(f"Nieznany klucz preprocess.{key} w {source}.")
                elif not isinstance(preprocess[key], bool):
                    errors.append(f"preprocess.{key} musi być wartością logiczną (true/false).")
            normalized.setdefault("preprocess_options", preprocess)

    if errors:
        raise ValueError("\n".join(errors))

    return normalized


config = load_config()
