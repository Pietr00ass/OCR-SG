import pytest

pytest.importorskip("cv2", exc_type=ImportError)

from ocr_app.core.worker import PageTask, process_page
from ocr_app.core.ocr_engine import OcrResult, OcrEngine
from ocr_app.core.postprocess import clean_text, merge_pages
from tests.test_image_preprocess import _generate_sample_image


def test_full_pipeline_with_mocked_ocr(monkeypatch, tmp_path):
    image = _generate_sample_image()
    image_path = tmp_path / "sample_image.png"
    image.save(image_path)

    def fake_run(self, processed_image):
        # Ensure preprocessing produced an image we can read
        assert processed_image.size == image.size
        return OcrResult(text=" Hello OCR \n\n")

    monkeypatch.setattr(OcrEngine, "run", fake_run)

    task = PageTask(
        source_file=image_path,
        page_index=0,
        engine_name="tesseract",
        languages=["eng"],
        preprocess_options={
            "grayscale": True,
            "denoise": True,
            "threshold": True,
            "scale_up": False,
            "deskew": False,
            "remove_background": False,
        },
    )

    result = process_page(image, task)
    cleaned = clean_text([result.text])
    merged = merge_pages([cleaned])

    assert merged == "Hello OCR"
