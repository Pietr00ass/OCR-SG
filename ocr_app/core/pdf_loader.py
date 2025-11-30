"""Utilities to load PDF pages into images."""
from __future__ import annotations

from pathlib import Path
from typing import Generator, Optional, Tuple

import fitz  # PyMuPDF
from PIL import Image


def load_pdf_pages(pdf_path: Path, dpi: int = 300) -> Generator[Tuple[int, Image.Image], None, None]:
    """Yield pages from a PDF as PIL Images at the requested DPI."""
    doc = fitz.open(pdf_path)
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    for page_index in range(len(doc)):
        page = doc.load_page(page_index)
        pix = page.get_pixmap(matrix=matrix)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        yield page_index, img


def count_pages(pdf_path: Path) -> int:
    """Return the number of pages in the PDF file."""
    with fitz.open(pdf_path) as doc:
        return len(doc)
