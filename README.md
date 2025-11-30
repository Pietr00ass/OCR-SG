# Best-in-class OCR GUI (design draft)

## Wymagania systemowe
- **Systemy**: Windows 10/11 (64-bit), Ubuntu 20.04+/Debian 11+, macOS 12+.
- **Python**: 3.10–3.12 (64-bit; wymagane dla PyTorch/PyQt6).
- **Biblioteki systemowe**:
  - Linux: `libgl1` (PyQt6), `poppler-utils` (dla konwersji PDF jeśli chcesz alternatywę do PyMuPDF), `tesseract-ocr` + pakiety językowe.
  - Windows: najnowszy **VC++ Redistributable x64** (sekcja niżej), lokalnie zainstalowany Tesseract.
  - macOS: `brew install tesseract` oraz opcjonalnie `brew install poppler`.
- **GPU (opcjonalnie)**: karta NVIDIA z obsługą CUDA 11.8+ jeżeli chcesz używać wariantu GPU PyTorch/EasyOCR.

## Instalacja
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```
Jeśli chcesz uruchomić build z CUDA, po instalacji wykonaj kroki z sekcji „PyTorch działający na każdym środowisku (CPU i CUDA)”.

## Przykłady użycia
### GUI / CLI
- GUI: `python main.py`
- CLI (tryb wsadowy, przykład OCR jednego pliku bez GUI):
  ```bash
  python - <<'PY'
from ocr_app.core.ocr_engine import OCREngine
from ocr_app.core.pdf_loader import load_pdf

pages = load_pdf("sample.pdf", dpi=300)
engine = OCREngine(engine_name="tesseract", languages=["pol", "eng"])
text = engine.run_ocr(pages)
print(text[:500])
PY
  ```

### API (fragment konfiguracji w kodzie)
```python
from ocr_app.config import Config

cfg = Config()
cfg.tesseract_cmd = r"C:/Program Files/Tesseract-OCR/tesseract.exe"
cfg.default_languages = ["pol", "eng"]
```
Następnie przekaż `cfg` do komponentów GUI/workerów (np. podczas tworzenia `MainWindow` lub `OCREngine`).

## Architektura i pipeline
Aplikacja jest modułowa i dzieli się na warstwę GUI (PyQt6), logikę OCR oraz narzędzia pomocnicze. Główne kroki przetwarzania: wczytanie plików (PDF/obrazy) → konwersja stron do obrazów (`core/pdf_loader.py`) → preprocessing w OpenCV (`core/image_preprocess.py`) sterowany z GUI → OCR wybranym silnikiem (`core/ocr_engine.py`) w procesach roboczych (`core/worker.py`) → czyszczenie tekstu (`core/postprocess.py`) → eksport (`core/exporter.py`). Logowanie jest scentralizowane w `logging_utils.py` i widoczne w GUI.

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

### Struktura projektu
- `ocr_app/core/` – logika OCR (ładowanie PDF, preprocessing, silnik OCR, eksport).
- `ocr_app/gui/` – komponenty PyQt6 i widoki.
- `ocr_app/config.py` – konfiguracja domyślna oraz rejestr obsługiwanych języków/silników.
- `main.py` – bootstrap aplikacji (GUI).

#### Dodawanie nowych języków / modelu
1. Dodaj kod języka do `available_languages` w `ocr_app/config.py` (oraz pliki językowe Tesseract/PaddleOCR w systemie).
2. Jeśli to nowy model (np. własny checkpoint EasyOCR/PaddleOCR), skonfiguruj ścieżkę i parametry w `ocr_app/core/ocr_engine.py` oraz w konfiguracji (np. `custom_model_dir`).
3. Rozszerz GUI o wybór nowego języka/modelu (menu w `ocr_app/gui/main_window.py`) i przekaż ustawienia do workerów.

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

## Ewaluacja CER/WER
- Przykładowy zestaw referencyjny znajduje się w `samples/ground_truth.json` (pola `id`, `ground_truth`, `prediction`).
- Uruchomienie: `python scripts/eval_cer.py` (opcjonalnie `--dataset <ścieżka_do_json>`).
- Na dołączonym zestawie uzyskujemy: **CER = 4.76%**, **WER = 22.73%**.

### Rozwiązywanie problemów
- Błąd `ModuleNotFoundError: No module named 'fitz'`: biblioteka PyMuPDF nie jest zainstalowana w środowisku, z którego uruchamiasz aplikację. Zainstaluj ją poleceniem `pip install PyMuPDF` lub ponownie wykonaj `pip install -r requirements.txt`, upewniając się, że korzystasz z tego samego interpretera Pythona, którego używa IDE.
- Błąd `ImportError: libGL.so.1`: system nie posiada biblioteki OpenGL wymaganej przez PyQt6. Na Debianie/Ubuntu zainstaluj ją poleceniem `sudo apt-get install libgl1` (lub na RedHat/Fedora `sudo dnf install mesa-libGL`). W kontenerach warto też ustawić zmienne środowiskowe wymuszające tryb offscreen (robimy to automatycznie w `ocr_app/app.py`).
- Błąd `ImportError/ModuleNotFoundError: cannot import name 'QtWidgets' from 'PyQt6'`: środowisko nie ma pełnej instalacji PyQt6 (brak modułu QtWidgets). Uruchom `pip install --no-cache-dir -r requirements.txt`, a na Windows upewnij się, że interpreter jest 64-bitowy oraz zainstalowano najnowszy VC++ Redistributable (sekcja poniżej).

### Instalacja Microsoft Visual C++ Redistributable (Windows)
Jeśli PyTorch lub inne biblioteki zgłaszają błąd ładowania DLL (np. `c10.dll`), zwykle pomaga doinstalowanie najnowszych pakietów VC++:
1. Wejdź na oficjalną stronę Microsoft: [Latest supported Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist).
2. Pobierz instalator **x64** (plik `…vc_redist.x64.exe`). Na 32-bitowych systemach dodatkowo `vc_redist.x86.exe`, ale dla większości współczesnych systemów wystarczy x64.
3. Uruchom instalator jako administrator i zakończ kreator (opcje domyślne są wystarczające).
4. Po instalacji zrestartuj komputer, aby nowe biblioteki zostały zarejestrowane.
5. Jeśli błąd dotyczy aplikacji uruchamianej z wirtualnego środowiska, upewnij się, że używasz zgodnej wersji Pythona (64-bit) oraz odpowiedniego wariantu pakietu (np. CPU vs CUDA dla PyTorch).

### PyTorch działający na każdym środowisku (CPU i CUDA)
Domyślnie `requirements.txt` pobiera **uniwersalne buildy CPU** z repozytorium PyTorch (`--extra-index-url https://download.pytorch.org/whl/cpu`), więc instalacja `python -m pip install -r requirements.txt` zadziała na Windows/Linux/Mac bez CUDA.

Jeśli masz kartę NVIDIA i chcesz użyć GPU:
1. Odinstaluj build CPU: `python -m pip uninstall torch torchvision torchaudio -y`.
2. Zainstaluj wariant CUDA dopasowany do sterownika według polecenia z [pytorch.org/get-started/locally](https://pytorch.org/get-started/locally) (np. `pip install torch==2.3.1+cu121 torchvision==0.18.1+cu121 torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cu121`).
3. Zweryfikuj instalację:
   ```bash
   python - <<'PY'
import torch
print('torch', torch.__version__)
print('CUDA dostępne:', torch.cuda.is_available())
print('Urządzenia CUDA:', torch.cuda.device_count())
PY
   ```
   Jeśli CUDA pozostaje niedostępna, zaktualizuj sterownik GPU i upewnij się, że używasz zgodnego pakietu (np. `cu118`, `cu121`).

Zasady niezawodności:
- Używaj 64-bitowego Pythona (sprawdź: `python -c "import platform; print(platform.architecture())"`).
- Czyść stare instalacje przed zmianą wariantu (`pip uninstall torch torchvision torchaudio -y`).
- W kodzie wywołuj `torch.cuda.is_available()` i przełączaj na CPU, gdy CUDA nie jest dostępna, aby aplikacja działała wszędzie.

### PaddleOCR wyłącznie na CPU
- `requirements.txt` wymusza instalację **CPU-only** poprzez pin do `paddlepaddle==2.6.2` i źródło kółek `--find-links https://www.paddlepaddle.org.cn/whl/cpu` (co zapobiega przypadkowemu pobraniu `paddlepaddle-gpu`).
- Jeśli wcześniej był zainstalowany wariant GPU, wykonaj `pip uninstall paddlepaddle-gpu paddlepaddle paddleocr -y`, a następnie ponownie `pip install -r requirements.txt`.
- Na Windows upewnij się, że masz zainstalowany najnowszy **Microsoft Visual C++ Redistributable (x64)**; brak runtime'ów często powoduje błędy DLL podczas ładowania PaddleOCR.
- Jeśli mimo to podczas importu pojawia się `WinError 1114` (błąd inicjowania procedury DLL), najczęściej pomaga: ponowne odinstalowanie wariantów GPU (`pip uninstall paddlepaddle-gpu paddlepaddle paddleocr -y`), reinstalacja CPU (`pip install --no-cache-dir -r requirements.txt`), instalacja pakietu VC++ 2015–2022 x64 oraz restart IDE/środowiska przed ponownym uruchomieniem aplikacji. Po reinstalacji zweryfikuj w Pythonie: `from paddleocr import PaddleOCR; PaddleOCR()`.

#### Błędy z c10.dll (PyTorch/EasyOCR/PaddleOCR)
- Komunikat `WinError 1114` z odwołaniem do `c10.dll` zwykle oznacza pozostawione artefakty po instalacji GPU PyTorch albo brak VC++ runtime.
- Wyczyść wszystkie zależności OCR i zainstaluj je ponownie w wersji CPU, bez cache:
  ```bash
  python -m pip uninstall -y torch torchvision torchaudio paddlepaddle paddleocr easyocr
  python -m pip install --no-cache-dir -r requirements.txt
  ```
- Upewnij się, że w `requirements.txt` masz linię `--extra-index-url https://download.pytorch.org/whl/cpu` (domyślnie w repozytorium jest obecna) i korzystasz z 64-bitowego Pythona.
- Zainstaluj **VC++ 2015–2022 x64** (sekcja powyżej), a po reinstalacji biblioteki zweryfikuj w interpreterze `import torch; import paddleocr`.

#### Brak fontów PyQt6 (QFontDatabase)
- PyQt6 nie dostarcza już fontów; jeśli w logach widzisz komunikat `Cannot find font directory .../PyQt6/Qt6/lib/fonts`, doinstaluj zestaw fontów (np. [DejaVu](https://dejavu-fonts.github.io/)).
- Skopiuj katalog czcionek do folderu projektu i ustaw zmienną środowiskową przed startem aplikacji, np. na Windows:
  ```powershell
  $env:QT_QPA_FONTDIR="C:\\Users\\<użytkownik>\\source\\repos\\OCR-SG\\fonts"
  python main.py
  ```
- Alternatywnie zainstaluj fonty systemowo, aby PyQt6 mógł je odnaleźć bez konfiguracji zmiennych środowiskowych.

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
