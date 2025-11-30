import numpy as np
import pytest
from PIL import Image, ImageDraw

pytest.importorskip("cv2", exc_type=ImportError)

from ocr_app.core.image_preprocess import preprocess_image


def _generate_sample_image(width: int = 120, height: int = 60) -> Image.Image:
    image = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.text((10, 20), "Hello", fill=(0, 0, 0))
    return image


def test_preprocess_applies_grayscale_and_threshold():
    image = _generate_sample_image()

    processed, metrics = preprocess_image(
        image,
        {
            "grayscale": True,
            "denoise": True,
            "threshold": True,
            "scale_up": False,
            "deskew": False,
            "remove_background": False,
        },
    )

    assert metrics == {}
    arr = np.array(processed)
    # image should stay the same size and be in RGB mode
    assert processed.size == image.size
    assert processed.mode == "RGB"
    # Grayscale + threshold should lead to equal channels with binary values
    first_channel = arr[:, :, 0]
    assert np.array_equal(first_channel, arr[:, :, 1])
    assert np.array_equal(first_channel, arr[:, :, 2])
    assert set(np.unique(first_channel)).issubset({0, 255})
