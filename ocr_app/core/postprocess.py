"""Text postprocessing utilities."""
from __future__ import annotations

from typing import List


def clean_text(lines: List[str]) -> str:
    """Strip whitespace and remove empty lines."""
    cleaned = [line.strip() for line in lines if line.strip()]
    return "\n".join(cleaned)


def merge_pages(pages: List[str]) -> str:
    """Join page texts with separators."""
    return "\n\n".join(pages)
