# Contributing to OCR-Devnagari

Thank you for your interest in contributing! This project digitizes sacred Hindi, Sanskrit, and Devanagari manuscripts using AI-powered OCR.

## Development Setup

### Prerequisites

- **Python 3.10+**
- **[UV](https://docs.astral.sh/uv/)** — fast Python package manager
- **[Poppler](https://poppler.freedesktop.org/)** — PDF rendering
- **Google Cloud account** (for Gemini/Vertex AI features)

### Install

```bash
# Clone the repository
git clone https://github.com/rajeshkanaka/OCR-Devnagari.git
cd OCR-Devnagari

# Install all dependencies (including dev tools)
uv sync --all-extras

# Install poppler (macOS)
brew install poppler

# Install poppler (Ubuntu/Debian)
sudo apt install poppler-utils
```

### Optional backends

```bash
# EasyOCR (for hybrid/easyocr engine)
uv pip install easyocr

# Tesseract (for tesseract engine)
brew install tesseract tesseract-lang          # macOS
sudo apt install tesseract-ocr tesseract-ocr-hin tesseract-ocr-san  # Ubuntu
```

### Configure API access

```bash
# Option A: API Key
export GEMINI_API_KEY="your-key"

# Option B: Vertex AI (recommended for production)
export GOOGLE_CLOUD_PROJECT="your-project"
export GOOGLE_CLOUD_LOCATION="global"
export GOOGLE_GENAI_USE_VERTEXAI=1
gcloud auth application-default login
```

## Running the Project

```bash
# CLI — process a PDF
uv run python -m ocr_hindi ocr book.pdf -e gemini --pages all

# Streamlit UI
uv run streamlit run src/ocr_hindi/app.py

# Validate setup
uv run python -m ocr_hindi validate
```

## Code Quality

```bash
# Format code
uv run black src/

# Lint
uv run ruff check src/

# Type check
uv run mypy src/ocr_hindi/

# Run tests
uv run pytest
```

## Project Structure

```
src/ocr_hindi/
├── __init__.py          # Package exports
├── cli.py               # Typer CLI commands
├── app.py               # Streamlit web UI
├── processor.py         # Single-file OCR processor
├── multi_processor.py   # Multi-page parallel processor
├── async_processor.py   # Async processing support
├── batch_processor.py   # GCS batch processing
├── search.py            # SQLite FTS5 search index
├── cache.py             # Crash-safe page cache
├── prompts.py           # Gemini prompt templates
├── utils.py             # Shared utilities
└── backends/
    ├── base.py           # Abstract OCR backend
    ├── gemini_backend.py # Gemini 2.0 Flash
    ├── hybrid_backend.py # EasyOCR + Gemini routing
    ├── easyocr_backend.py
    ├── tesseract_backend.py
    ├── marker_backend.py
    └── mantra_detector.py
```

## How to Contribute

### Reporting Bugs

Use the [Bug Report template](https://github.com/rajeshkanaka/OCR-Devnagari/issues/new?template=bug_report.md) and include:
- Steps to reproduce
- Expected vs actual behavior
- Python version, OS, engine used

### Suggesting Features

Use the [Feature Request template](https://github.com/rajeshkanaka/OCR-Devnagari/issues/new?template=feature_request.md).

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Run linters and tests: `uv run ruff check src/ && uv run pytest`
5. Commit with a clear message: `git commit -m "Add your feature"`
6. Push: `git push origin feature/your-feature`
7. Open a Pull Request

### PR Guidelines

- Keep PRs focused — one feature/fix per PR
- Add tests for new functionality
- Update documentation if adding user-facing features
- Follow existing code style (Black formatting, ruff linting)
- Use `from __future__ import annotations` for modern type hints

## Areas Looking for Help

- **New OCR backends** — integration with other OCR engines
- **Language support** — extending beyond Hindi/Sanskrit to other Indic scripts
- **Test coverage** — unit and integration tests
- **Documentation** — tutorials, guides, examples
- **UI improvements** — Streamlit interface enhancements
- **Performance** — optimizing processing speed and memory usage

## Code of Conduct

Be respectful and constructive. This project serves the spiritual and academic community — let's keep interactions positive and inclusive.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
