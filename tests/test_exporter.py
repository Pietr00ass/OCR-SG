from pathlib import Path

import docx

from ocr_app.core.exporter import export_docx, export_txt


def test_export_txt_writes_pages(tmp_path):
    pages = ["Pierwsza linia", "Druga linia"]
    output = tmp_path / "result.txt"

    export_txt(output, pages)

    content = output.read_text(encoding="utf-8").splitlines()
    assert content == ["Pierwsza linia", "", "Druga linia"]


def test_export_docx_contains_headings_and_text(tmp_path):
    pages = ["Strona jeden", "Strona dwa"]
    output = tmp_path / "result.docx"

    export_docx(output, pages)

    assert output.exists()
    document = docx.Document(output)
    paragraphs = [p.text for p in document.paragraphs]

    assert paragraphs[0] == "Page 1"
    assert paragraphs[1] == "Strona jeden"
    assert paragraphs[2] == "Page 2"
    assert paragraphs[3] == "Strona dwa"
