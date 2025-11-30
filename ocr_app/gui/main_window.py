"""PyQt6 GUI for the OCR application."""
from __future__ import annotations

from pathlib import Path
from typing import List

from PyQt6 import QtCore, QtGui, QtWidgets

from ..config import config
from ..core import pdf_loader
from ..core.image_preprocess import preprocess_image
from ..core.worker import PageTask, process_page
from ..logging_utils import setup_logging


class MainWindow(QtWidgets.QMainWindow):
    """Main application window."""

    log_signal = QtCore.pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        config.ensure_dirs()
        self.logger = setup_logging(gui_signal=self.log_signal)
        self._build_ui()
        self.log_signal.connect(self._append_log)

    def _build_ui(self) -> None:
        self.setWindowTitle("Best-in-class OCR")
        self.resize(1100, 700)
        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)

        controls = QtWidgets.QHBoxLayout()
        self.add_files_btn = QtWidgets.QPushButton("Dodaj pliki")
        self.add_files_btn.clicked.connect(self._select_files)
        controls.addWidget(self.add_files_btn)

        self.engine_combo = QtWidgets.QComboBox()
        self.engine_combo.addItems(["tesseract", "paddleocr", "easyocr"])
        default_engine_index = self.engine_combo.findText(config.default_engine)
        if default_engine_index != -1:
            self.engine_combo.setCurrentIndex(default_engine_index)
        controls.addWidget(QtWidgets.QLabel("Silnik:"))
        controls.addWidget(self.engine_combo)

        self.lang_list = QtWidgets.QListWidget()
        for lang in config.available_languages:
            item = QtWidgets.QListWidgetItem(lang)
            item.setCheckState(
                QtCore.Qt.CheckState.Checked
                if lang in config.default_languages
                else QtCore.Qt.CheckState.Unchecked
            )
            self.lang_list.addItem(item)
        lang_group = QtWidgets.QGroupBox("Języki")
        lang_layout = QtWidgets.QVBoxLayout(lang_group)
        lang_layout.addWidget(self.lang_list)
        controls.addWidget(lang_group)

        self.dpi_spin = QtWidgets.QSpinBox()
        self.dpi_spin.setRange(72, 600)
        self.dpi_spin.setValue(config.pdf_dpi)
        controls.addWidget(QtWidgets.QLabel("PDF DPI"))
        controls.addWidget(self.dpi_spin)

        self.preprocess_checks = {}
        prep_group = QtWidgets.QGroupBox("Preprocessing")
        prep_layout = QtWidgets.QVBoxLayout(prep_group)
        for key, default in config.preprocess_options.items():
            cb = QtWidgets.QCheckBox(key)
            cb.setChecked(default)
            self.preprocess_checks[key] = cb
            prep_layout.addWidget(cb)
        controls.addWidget(prep_group)

        self.start_btn = QtWidgets.QPushButton("Start OCR")
        self.start_btn.clicked.connect(self._start_ocr)
        controls.addWidget(self.start_btn)

        controls.addStretch()
        layout.addLayout(controls)

        self.file_list = QtWidgets.QListWidget()
        self.file_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.file_list.setAcceptDrops(True)
        self.file_list.dragEnterEvent = self._drag_enter
        self.file_list.dropEvent = self._drop_event
        layout.addWidget(self.file_list)

        split = QtWidgets.QSplitter()
        self.log_view = QtWidgets.QTextEdit()
        self.log_view.setReadOnly(True)
        self.preview_orig = QtWidgets.QLabel("Podgląd oryginału")
        self.preview_proc = QtWidgets.QLabel("Podgląd po preprocessingu")
        self.preview_orig.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.preview_proc.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        split.addWidget(self.log_view)
        preview_split = QtWidgets.QSplitter()
        preview_split.addWidget(self.preview_orig)
        preview_split.addWidget(self.preview_proc)
        split.addWidget(preview_split)
        layout.addWidget(split)

        self.result_text = QtWidgets.QTextEdit()
        layout.addWidget(self.result_text)

        self.setCentralWidget(central)

    def _drag_enter(self, event: QtGui.QDragEnterEvent) -> None:  # type: ignore[override]
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _drop_event(self, event: QtGui.QDropEvent) -> None:  # type: ignore[override]
        for url in event.mimeData().urls():
            self._add_file(Path(url.toLocalFile()))

    def _append_log(self, message: str) -> None:
        self.log_view.append(message)

    def _select_files(self) -> None:
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, "Wybierz pliki", str(Path.home()), "Dokumenty (*.pdf *.jpg *.png *.tiff *.bmp *.webp)"
        )
        for file in files:
            self._add_file(Path(file))

    def _add_file(self, path: Path) -> None:
        if not path.exists():
            return
        item = QtWidgets.QListWidgetItem(str(path))
        self.file_list.addItem(item)

    def _selected_languages(self) -> List[str]:
        langs = []
        for i in range(self.lang_list.count()):
            item = self.lang_list.item(i)
            if item.checkState() == QtCore.Qt.CheckState.Checked:
                langs.append(item.text())
        return langs or config.default_languages

    def _preprocess_options(self) -> dict:
        return {key: cb.isChecked() for key, cb in self.preprocess_checks.items()}

    def _start_ocr(self) -> None:
        files = [Path(self.file_list.item(i).text()) for i in range(self.file_list.count())]
        if not files:
            QtWidgets.QMessageBox.warning(self, "Brak plików", "Dodaj pliki do przetworzenia")
            return
        languages = self._selected_languages()
        engine_name = self.engine_combo.currentText()
        dpi = self.dpi_spin.value()
        preprocess_opts = self._preprocess_options()

        results = []
        for file_path in files:
            if file_path.suffix.lower() == ".pdf":
                try:
                    page_images = [img for _, img in pdf_loader.load_pdf_pages(file_path, dpi=dpi)]
                except Exception as exc:  # pragma: no cover - GUI dialog
                    self.logger.exception("Nie udało się wczytać PDF: %s", file_path)
                    QtWidgets.QMessageBox.critical(
                        self,
                        "Błąd PDF",
                        f"Nie udało się wczytać pliku {file_path.name}: {exc}",
                    )
                    continue
            else:
                from PIL import Image

                try:
                    page_images = [Image.open(file_path)]
                except Exception as exc:  # pragma: no cover - GUI dialog
                    self.logger.exception("Nie udało się wczytać obrazu: %s", file_path)
                    QtWidgets.QMessageBox.critical(
                        self,
                        "Błąd obrazu",
                        f"Nie udało się otworzyć pliku {file_path.name}: {exc}",
                    )
                    continue

            page_texts = []
            for page_index, image in enumerate(page_images):
                task = PageTask(
                    source_file=file_path,
                    page_index=page_index,
                    engine_name=engine_name,
                    languages=languages,
                    preprocess_options=preprocess_opts,
                    tesseract_cmd=config.tesseract_cmd,
                    model_config=config.models,
                )
                processed, _ = preprocess_image(image, preprocess_opts)
                # Update previews for the last processed page
                self._update_previews(image, processed)
                result = process_page(image, task, preprocessed=processed)
                page_texts.append(result.text)
            results.append("\n\n".join(page_texts))

        self.result_text.setPlainText("\n\n".join(results))

    def _update_previews(self, original, processed) -> None:
        def to_pixmap(img) -> QtGui.QPixmap:
            from PIL import ImageQt

            qim = ImageQt.ImageQt(img)
            return QtGui.QPixmap.fromImage(qim)

        self.preview_orig.setPixmap(
            to_pixmap(original).scaled(400, 400, QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        )
        self.preview_proc.setPixmap(
            to_pixmap(processed).scaled(400, 400, QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        )
