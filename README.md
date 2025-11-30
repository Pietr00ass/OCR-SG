# Best-in-class OCR GUI (design draft)

## Architektura i pipeline
Aplikacja jest modułowa i dzieli się na warstwę GUI (PyQt5), logikę OCR oraz narzędzia pomocnicze. Główne kroki przetwarzania: wczytanie plików (PDF/obrazy) → konwersja stron do obrazów (`core/pdf_loader.py`) → preprocessing w OpenCV (`core/image_preprocess.py`) sterowany z GUI → OCR wybranym silnikiem (`core/ocr_engine.py`) w procesach roboczych (`core/worker.py`) → czyszczenie tekstu (`core/postprocess.py`) → eksport (`core/exporter.py`). Logowanie jest scentralizowane w `logging_utils.py` i widoczne w GUI.

## Kluczowe pliki
```
ocr_app/
├─ app.py                 # bootstrap GUI
├─ config.py              # domyślne ustawienia, języki, DPI, ścieżka do tesseract
├─ logging_utils.py       # logger do pliku/konsoli/GUI
├─ gui/main_window.py     # główne okno, drag & drop, ustawienia, podglądy
└─ core/
   ├─ pdf_loader.py       # wczytywanie stron PDF (PyMuPDF)
   ├─ image_preprocess.py # grayscale/denoise/threshold/deskew/scale/bg removal
   ├─ ocr_engine.py       # wybór: Tesseract / PaddleOCR / EasyOCR
   ├─ worker.py           # jednostkowy proces stron
   ├─ postprocess.py      # czyszczenie i łączenie tekstu
   └─ exporter.py         # zapis TXT/DOCX
main.py                    # punkt startowy
```

## Konfiguracja (config.py / przykład JSON)
Domyślną konfigurację trzymamy w `ocr_app/config.py`. Kluczowe opcje: `tesseract_cmd` (ścieżka do binarki na Windows), `pdf_dpi`, `available_languages`, `default_languages`, `max_workers`, `preprocess_options`. Przykładowy JSON, jeśli chcesz mieć zewnętrzny plik:
```json
{
  "tesseract_cmd": "C:/Program Files/Tesseract-OCR/tesseract.exe",
  "default_engine": "tesseract",
  "available_languages": ["pol", "eng", "deu"],
  "default_languages": ["pol", "eng"],
  "pdf_dpi": 300,
  "max_workers": 4,
  "preprocess_options": {
    "grayscale": true,
    "denoise": true,
    "threshold": true,
    "deskew": true,
    "scale_up": true,
    "remove_background": false
  }
}
```

## Uruchomienie
1. Zainstaluj zależności: `pip install -r requirements.txt`.
2. Ustaw ścieżkę do Tesseract (Windows) w `ocr_app/config.py` (`tesseract_cmd = "C:/Program Files/Tesseract-OCR/tesseract.exe"`).
3. Start aplikacji: `python main.py`.
4. Budowa .exe (przykład): `pyinstaller --noconsole --onefile --name ocr_app main.py` (upewnij się, że katalog z modelami Paddle/EasyOCR jest dołączony, jeśli ich używasz).

### Rozwiązywanie problemów
- Błąd `ModuleNotFoundError: No module named 'fitz'`: biblioteka PyMuPDF nie jest zainstalowana w środowisku, z którego uruchamiasz aplikację. Zainstaluj ją poleceniem `pip install PyMuPDF` lub ponownie wykonaj `pip install -r requirements.txt`, upewniając się, że korzystasz z tego samego interpretera Pythona, którego używa IDE.

### Microsoft Visual Studio (Python) – najczęstsze problemy
1. **Ustaw właściwe środowisko**: w Visual Studio przejdź do **Python Environments** i wybierz interpretera, którego faktycznie używasz (np. `C:\Users\<user>\AppData\Local\Programs\Python\Python312\python.exe`). Jeśli pracujesz w wirtualnym środowisku, dodaj je jako nowe środowisko i ustaw jako domyślne dla solution.
2. **Instaluj paczki w tym samym interpreterze**: w oknie wybranego środowiska kliknij **Manage Packages** i zainstaluj `PyMuPDF` albo użyj polecenia `python -m pip install -r requirements.txt` uruchomionego z tego samego interpretera (np. z wbudowanego **Python Interactive**). Unikaj gołego `pip`, jeśli wskazuje inny interpreter.
3. **Zweryfikuj instalację**: w Visual Studio uruchom w **Python Interactive** polecenie `python -m pip show PyMuPDF` – jeśli paczka nie jest widoczna, zainstaluj ją tam ponownie.
4. **Ścieżka do Tesseract**: w `ocr_app/config.py` ustaw `tesseract_cmd` na lokalizację binarki (np. `"C:/Program Files/Tesseract-OCR/tesseract.exe"`); Visual Studio użyje tej samej konfiguracji co przy zwykłym uruchomieniu.

## Rozwój i dalsze pomysły
- Profile preprocessingu zapisywane do pliku (np. JSON) i wybierane w GUI.
- Kolejka zadań (np. Celery/Redis) do batchów w tle i komunikacji sieciowej.
- Cache modeli i stron dla szybszych iteracji na trudnych dokumentach.
- Eksport PDF z warstwą tekstową (np. PyMuPDF) jako dodatkowy moduł.
- Testy jednostkowe pipelinu preprocessingu i eksportu.
