from pathlib import Path

import pytest

fitz = pytest.importorskip("fitz")

from ocr_app.core.pdf_loader import count_pages, load_pdf_pages


def _make_sample_pdf(path: Path) -> None:
    doc = fitz.open()
    for number in (1, 2):
        page = doc.new_page()
        page.insert_text((72, 72), f"Sample page {number}")
    doc.save(path)


def test_count_pages_returns_length(tmp_path):
    pdf_path = tmp_path / "sample_document.pdf"
    _make_sample_pdf(pdf_path)
    assert count_pages(pdf_path) == 2


def test_load_pdf_pages_yields_images(tmp_path):
    pdf_path = tmp_path / "sample_document.pdf"
    _make_sample_pdf(pdf_path)
    pages = list(load_pdf_pages(pdf_path, dpi=72))
    assert len(pages) == 2
    for index, image in pages:
        assert isinstance(index, int)
        assert image.mode == "RGB"
        assert image.size[0] > 0 and image.size[1] > 0
