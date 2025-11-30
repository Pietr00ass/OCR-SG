"""FastAPI entrypoint exposing OCR capabilities."""
from __future__ import annotations

import mimetypes
import urllib.request
from pathlib import Path
from typing import List, Optional

from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from .config import config
from .core.ocr_service import PageOcrResult, run_ocr_on_bytes, run_ocr_on_path
from .logging_utils import setup_logging

logger = setup_logging()
app = FastAPI(title="OCR Service")


class BoundingBox(BaseModel):
    x: int
    y: int
    width: int
    height: int


class BoxResult(BaseModel):
    text: str
    bbox: BoundingBox
    confidence: Optional[float] = None


class PageResponse(BaseModel):
    page: int
    text: str
    confidence: Optional[float] = None
    boxes: List[BoxResult]


class OcrResponse(BaseModel):
    source: str
    engine: str
    languages: List[str]
    pages: List[PageResponse]


def _build_response(source: str, engine: str, languages: List[str], pages: List[PageOcrResult]) -> OcrResponse:
    return OcrResponse(
        source=source,
        engine=engine,
        languages=languages,
        pages=[
            PageResponse(
                page=page.page_index,
                text=page.text,
                confidence=page.confidence,
                boxes=[
                    BoxResult(
                        text=box.get("text", ""),
                        bbox=BoundingBox(
                            x=int((box.get("bbox") or {}).get("x", 0)),
                            y=int((box.get("bbox") or {}).get("y", 0)),
                            width=int((box.get("bbox") or {}).get("width", 0)),
                            height=int((box.get("bbox") or {}).get("height", 0)),
                        ),
                        confidence=box.get("confidence"),
                    )
                    for box in page.boxes
                ],
            )
            for page in pages
        ],
    )


@app.get("/health")
def health() -> dict:
    """Simple healthcheck endpoint."""

    return {"status": "ok"}


def _download_url(url: str) -> tuple[bytes, str]:
    try:
        with urllib.request.urlopen(url) as response:  # nosec: B310 - controlled input
            content_type = response.headers.get_content_type()
            payload = response.read()
            extension = mimetypes.guess_extension(content_type) or ""
            filename = Path(url).name or f"remote{extension}"
            return payload, filename
    except Exception as exc:  # pragma: no cover - network dependent
        logger.error("Nie udało się pobrać pliku z %s: %s", url, exc)
        raise HTTPException(status_code=400, detail="Nie udało się pobrać URL") from exc


@app.post("/ocr", response_model=OcrResponse)
async def perform_ocr(
    file: Optional[UploadFile] = File(default=None),
    url: Optional[str] = Form(default=None),
    engine: str = Form(default=config.default_engine),
    languages: Optional[List[str]] = Form(default=None),
    dpi: int = Form(default=config.pdf_dpi),
):
    """Run OCR on an uploaded file or remote URL."""

    selected_languages = languages or config.default_languages
    preprocess_options = config.preprocess_options

    if not file and not url:
        raise HTTPException(status_code=400, detail="Wymagany jest plik lub URL")

    if file:
        content = await file.read()
        pages = run_ocr_on_bytes(
            content,
            file.filename or "upload",
            engine,
            selected_languages,
            preprocess_options,
            dpi,
            config.tesseract_cmd,
        )
        return _build_response(file.filename or "upload", engine, selected_languages, pages)

    payload, filename = _download_url(url or "")
    pages = run_ocr_on_bytes(
        payload,
        filename,
        engine,
        selected_languages,
        preprocess_options,
        dpi,
        config.tesseract_cmd,
    )
    return _build_response(filename, engine, selected_languages, pages)


@app.post("/ocr/path", response_model=OcrResponse)
def perform_ocr_from_path(
    path: str = Body(..., embed=True),
    engine: str = Body(default=config.default_engine),
    languages: Optional[List[str]] = Body(default=None),
    dpi: int = Body(default=config.pdf_dpi),
):
    """Run OCR on a server-side path (useful for local deployments)."""

    target = Path(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Plik nie istnieje")

    selected_languages = languages or config.default_languages
    preprocess_options = config.preprocess_options

    try:
        pages = run_ocr_on_path(
            target,
            engine,
            selected_languages,
            preprocess_options,
            dpi,
            config.tesseract_cmd,
        )
    except Exception as exc:  # pragma: no cover - runtime errors
        logger.exception("OCR failed for %s", target)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return _build_response(str(target), engine, selected_languages, pages)
