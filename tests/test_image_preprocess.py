import numpy as np
import pytest
from PIL import Image, ImageDraw

from ocr_app.config import OCRConfig

pytest.importorskip("cv2", exc_type=ImportError)

from ocr_app.core.image_preprocess import preprocess_image  # noqa: E402


def _high_contrast_image(width: int = 80, height: int = 60) -> Image.Image:
    """Create a simple black/white pattern image."""

    image = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(image)
    for x in range(0, width, 8):
        fill = "black" if (x // 8) % 2 == 0 else "white"
        draw.rectangle([x, 0, x + 7, height], fill=fill)
    return image


def _color_gradient_image(width: int = 90, height: int = 60) -> Image.Image:
    """Create a small RGB gradient image for scale tests."""

    image = Image.new("RGB", (width, height))
    for x in range(width):
        for y in range(height):
            r = int(255 * x / (width - 1))
            g = int(255 * y / (height - 1))
            b = int(255 * (x + y) / (width + height - 2))
            image.putpixel((x, y), (r, g, b))
    return image


def test_config_contains_expected_preprocess_defaults():
    config = OCRConfig()
    assert config.preprocess_options == {
        "grayscale": True,
        "denoise": True,
        "threshold": True,
        "deskew": True,
        "scale_up": True,
        "remove_background": False,
    }


def test_preprocess_thresholds_high_contrast_image():
    image = _high_contrast_image()

    config = OCRConfig()
    options = {**config.preprocess_options, "scale_up": False, "deskew": False}

    processed, metrics = preprocess_image(image, options)

    assert metrics == {}
    arr = np.array(processed)
    assert processed.mode == "RGB"
    # thresholding should produce binary channels
    unique_values = np.unique(arr[:, :, 0])
    assert set(unique_values).issubset({0, 255})
    assert np.array_equal(arr[:, :, 0], arr[:, :, 1])
    assert np.array_equal(arr[:, :, 1], arr[:, :, 2])


def test_preprocess_respects_disabled_threshold_and_scale():
    image = _high_contrast_image()

    config = OCRConfig()
    options = {**config.preprocess_options}
    options.update({"threshold": False, "scale_up": False, "deskew": False})

    processed, _ = preprocess_image(image, options)

    arr = np.array(processed)
    assert processed.size == image.size
    # Without thresholding we expect more than two tone values
    assert len(np.unique(arr[:, :, 0])) > 2


def test_preprocess_scales_image_from_config():
    image = _color_gradient_image()

    config = OCRConfig()
    options = {**config.preprocess_options}
    options.update({"threshold": False, "deskew": False})

    processed, _ = preprocess_image(image, options)

    expected_size = (int(image.size[0] * 1.5), int(image.size[1] * 1.5))
    assert processed.size == expected_size
    # Pipeline keeps PIL RGB mode after conversions
    assert processed.mode == "RGB"
