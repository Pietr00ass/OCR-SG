from ocr_app.core.ocr_engine import OcrEngine, OcrResult
from tests.test_image_preprocess import _generate_sample_image


def test_tesseract_engine_uses_pytesseract(monkeypatch):
    captured = {}

    def fake_image_to_string(image, lang):
        captured["lang"] = lang
        captured["size"] = image.size
        return "mocked text"

    monkeypatch.setattr("pytesseract.image_to_string", fake_image_to_string)

    engine = OcrEngine(engine_name="tesseract", languages=["eng", "pol"])
    image = _generate_sample_image()

    result = engine.run(image)

    assert isinstance(result, OcrResult)
    assert result.text == "mocked text"
    assert captured["lang"] == "eng+pol"
    assert captured["size"] == image.size
