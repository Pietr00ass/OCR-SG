import pytest

pytest.importorskip("fitz")

from ocr_app.core.pdf_loader import count_pages, load_pdf_pages
from tests.test_image_preprocess import _generate_sample_image


def _create_sample_pdf(tmp_path) -> str:
    page1 = _generate_sample_image(80, 40)
    page2 = _generate_sample_image(100, 50)
    pdf_path = tmp_path / "sample_multipage.pdf"
    page1.save(pdf_path, "PDF", save_all=True, append_images=[page2])
    return pdf_path


def test_count_pages_returns_length(tmp_path):
    pdf_path = _create_sample_pdf(tmp_path)
    assert count_pages(pdf_path) == 2


def test_load_pdf_pages_yields_images(tmp_path):
    pdf_path = _create_sample_pdf(tmp_path)
    pages = list(load_pdf_pages(pdf_path, dpi=72))
    assert len(pages) == 2
    for index, image in pages:
        assert isinstance(index, int)
        assert image.mode == "RGB"
        assert image.size[0] > 0 and image.size[1] > 0
