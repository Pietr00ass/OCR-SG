import pytest
from pathlib import Path

from ocr_app.config import load_config


def test_load_config_unknown_root_key(tmp_path):
    cfg_path = tmp_path / "config.yml"
    cfg_path.write_text("""
foo: 123
""")

    with pytest.raises(ValueError) as excinfo:
        load_config(cfg_path)

    assert "Nieznany klucz na poziomie root: foo" in str(excinfo.value)


def test_load_config_invalid_model_paths_when_auto_download_disabled(tmp_path):
    cfg_path = tmp_path / "config.yml"
    cfg_path.write_text(
        """
models:
  paddleocr:
    det_model_dir: /nonexistent/det
  auto_download_missing: false
"""
    )

    with pytest.raises(ValueError) as excinfo:
        load_config(cfg_path)

    message = str(excinfo.value)
    assert "models.paddleocr" in message
    assert "/nonexistent/det" in message


def test_load_config_invalid_numeric_values(tmp_path):
    cfg_path = tmp_path / "config.yml"
    cfg_path.write_text(
        """
pdf:
  dpi: -10
app:
  max_workers: 0
"""
    )

    with pytest.raises(ValueError) as excinfo:
        load_config(cfg_path)

    message = str(excinfo.value)
    assert "pdf.dpi musi być dodatnią liczbą całkowitą" in message
    assert "app.max_workers musi być dodatnią liczbą całkowitą" in message
