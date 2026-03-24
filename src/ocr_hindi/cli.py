"""CLI interface for Hindi/Sanskrit PDF OCR with multiple backend support.

Backends available:

- gemini: Original Gemini Vision API (accurate but expensive)
- marker: Open-source PDF to Markdown (FREE)
- easyocr: Open-source OCR with Hindi support (FREE)
- tesseract: Google's open-source OCR (FREE)
- hybrid: EasyOCR + Gemini verification (90%+ savings)
"""

from __future__ import annotations

import asyncio
import json
import signal
import warnings
from datetime import datetime
from pathlib import Path

import typer
from pdf2image import pdfinfo_from_path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .async_processor import AsyncOCRConfig, AsyncOCRProcessor
from .multi_processor import MultiBackendProcessor, MultiProcessorConfig
from .processor import OCRConfig, OCRProcessor
from .utils import estimate_processing_time, format_duration, parse_page_range

# Suppress noisy torch warnings at import time
warnings.filterwarnings("ignore", message=".*pin_memory.*")
warnings.filterwarnings("ignore", category=UserWarning, module="torch")

app = typer.Typer(
    name="ocr-hindi",
    help="OCR tool for Hindi/Sanskrit PDFs using Gemini + Vertex AI",
    add_completion=False,
)
console = Console()

# Engine metadata used by the `ocr` command
_ENGINE_INFO: dict[str, dict[str, str]] = {
    "gemini": {
        "model": "gemini-2.0-flash",
        "cost": "~$0.50/1K pages",
        "badge": "[bold white on red] PREMIUM [/bold white on red]",
        "desc": "Maximum accuracy",
    },
    "hybrid": {
        "model": "EasyOCR + gemini-2.0-flash",
        "cost": "~$0.10/1K pages",
        "badge": "[bold white on green] RECOMMENDED [/bold white on green]",
        "desc": "Best value",
    },
    "easyocr": {
        "model": "EasyOCR (Local)",
        "cost": "FREE",
        "badge": "[bold black on yellow] FREE [/bold black on yellow]",
        "desc": "No API costs",
    },
    "marker": {
        "model": "Marker (Local)",
        "cost": "FREE",
        "badge": "[bold black on yellow] FREE [/bold black on yellow]",
        "desc": "Best for books",
    },
    "tesseract": {
        "model": "Tesseract (Local)",
        "cost": "FREE",
        "badge": "[bold black on yellow] FREE [/bold black on yellow]",
        "desc": "Basic OCR",
    },
}

_VALID_ENGINES = tuple(_ENGINE_INFO.keys())


def _version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"ocr-hindi version {__version__}")
        raise typer.Exit()


def _get_pdf_pages(pdf_path: Path) -> int:
    """Get total page count from a PDF, or exit on failure.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Total page count.
    """
    try:
        return pdfinfo_from_path(str(pdf_path))["Pages"]
    except Exception as exc:
        console.print(f"[red]Error reading PDF: {exc}[/red]")
        raise typer.Exit(1) from exc


def _resolve_page_list(
    pages: str | None, total_pages: int
) -> list[int]:
    """Resolve page specification to a list of page numbers.

    Prompts interactively if pages is None.

    Args:
        pages: Page specification string, or None to prompt.
        total_pages: Maximum page count.

    Returns:
        Sorted list of page numbers.
    """
    if pages is None:
        pages = typer.prompt(
            "Enter page range (e.g., all, 1-50, 1,5,10-20)",
            default="all",
        )

    try:
        return parse_page_range(pages, total_pages)
    except ValueError as exc:
        console.print(f"[red]Invalid page range: {exc}[/red]")
        raise typer.Exit(1) from exc


def _print_retry_hint(
    pdf_path: Path, command: str, engine: str = ""
) -> None:
    """Print hint for retrying failed pages.

    Args:
        pdf_path: Path to the PDF.
        command: CLI sub-command name (e.g., "process", "fast", "ocr").
        engine: Engine flag for the ocr command.
    """
    from .utils import ProgressState, get_progress_file

    progress_file = get_progress_file(pdf_path)
    state = ProgressState.load(progress_file)
    if state and state.failed_pages:
        failed_str = ",".join(str(p) for p in sorted(state.failed_pages))
        engine_flag = f" -e {engine}" if engine else ""
        console.print(
            f"\n[yellow]To retry failed pages:[/yellow]\n"
            f'  python -m ocr_hindi {command} {pdf_path}'
            f'{engine_flag} --pages "{failed_str}"'
        )


# ──────────────────────────────────────────────────────────────────────────────


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """OCR tool for Hindi/Sanskrit PDFs using Gemini + Vertex AI."""


@app.command()
def validate() -> None:
    """Validate authentication and dependencies."""
    import subprocess

    console.print(Panel.fit("[bold]OCR Hindi - Validation[/bold]"))
    console.print("\n[bold]Checking dependencies...[/bold]")
    deps_ok = True

    try:
        import google.genai  # noqa: F401

        console.print("  [green]\u2713[/green] google-genai")
    except ImportError:
        console.print("  [red]\u2717[/red] google-genai (not installed)")
        deps_ok = False

    try:
        from pdf2image import convert_from_path  # noqa: F401

        console.print("  [green]\u2713[/green] pdf2image")
    except ImportError:
        console.print("  [red]\u2717[/red] pdf2image (not installed)")
        deps_ok = False

    try:
        from PIL import Image  # noqa: F401

        console.print("  [green]\u2713[/green] pillow")
    except ImportError:
        console.print("  [red]\u2717[/red] pillow (not installed)")
        deps_ok = False

    try:
        subprocess.run(
            ["pdftoppm", "-v"], capture_output=True, text=True, timeout=5
        )
        console.print("  [green]\u2713[/green] poppler (pdftoppm)")
    except (subprocess.SubprocessError, FileNotFoundError):
        console.print(
            "  [red]\u2717[/red] poppler (required by pdf2image). "
            "Install with: brew install poppler"
        )
        deps_ok = False

    if not deps_ok:
        console.print("\n[red]Dependencies missing. Install with:[/red]")
        console.print("  uv pip install -r requirements.txt")
        console.print("  brew install poppler")
        raise typer.Exit(1)

    console.print("\n[bold]Checking authentication...[/bold]")
    processor = AsyncOCRProcessor()
    success, auth_method, message = processor.validate_auth()

    if success:
        console.print(f"  [green]\u2713[/green] {auth_method}: {message}")
        console.print("\n[green bold]Validation successful![/green bold]")
    else:
        console.print(f"  [red]\u2717[/red] {auth_method}: {message}")
        console.print("\n[red]Authentication failed.[/red]")
        console.print("\n[yellow]To fix:[/yellow]")
        console.print("  Option 1 (Vertex AI - Recommended):")
        console.print("    export GOOGLE_GENAI_USE_VERTEXAI=1")
        console.print("    export GOOGLE_CLOUD_PROJECT='your-project-id'")
        console.print("    export GOOGLE_CLOUD_LOCATION='global'")
        console.print("    gcloud auth application-default login")
        console.print("\n  Option 2 (API Key):")
        console.print("    export GEMINI_API_KEY='your-api-key'")
        raise typer.Exit(1)


@app.command()
def process(
    pdf_path: Path = typer.Argument(..., help="Path to the PDF file", exists=True),
    pages: str | None = typer.Option(
        None, "--pages", "-p", help="Page range (e.g., 'all', '1-50', '1,5,10-20')"
    ),
    resume: bool = typer.Option(False, "--resume", "-r", help="Resume from previous progress"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be processed"),
    model: str = typer.Option("gemini-2.0-flash", "--model", "-m", help="Gemini model to use"),
    dpi: int = typer.Option(200, "--dpi", help="DPI for PDF to image conversion"),
) -> None:
    """Process a PDF file and extract text using OCR."""
    console.print(Panel.fit(f"[bold]OCR Hindi - Processing[/bold]\n{pdf_path.name}"))

    total_pages = _get_pdf_pages(pdf_path)
    console.print(f"\n[bold]PDF Info:[/bold]")
    console.print(f"  Total pages: {total_pages}")

    page_list = _resolve_page_list(pages, total_pages)
    console.print(f"  Pages to process: {len(page_list)}")
    console.print(f"  Estimated time: {estimate_processing_time(len(page_list))}")

    if not dry_run:
        config = OCRConfig(model=model, dpi=dpi)
        processor = OCRProcessor(config=config)

        console.print("\n[bold]Validating authentication...[/bold]")
        success, auth_method, message = processor.validate_auth()

        if not success:
            console.print(f"[red]Authentication failed: {message}[/red]")
            console.print("Run 'python -m ocr_hindi validate' for help")
            raise typer.Exit(1)

        console.print(f"  [green]\u2713[/green] {auth_method}")

    try:
        if dry_run:
            processor = OCRProcessor(config=OCRConfig(model=model, dpi=dpi))
            processor.client = True  # Fake client for dry run
            processor.process_pdf(pdf_path, page_list, resume=resume, dry_run=True)
        else:
            successful, failed, output_path = processor.process_pdf(
                pdf_path, page_list, resume=resume
            )

            console.print("\n")
            console.print(
                Panel.fit(
                    f"[green bold]\u2713 OCR Complete![/green bold]\n\n"
                    f"Processed: {successful} pages\n"
                    f"Failed: {failed} pages\n"
                    f"Output: {output_path}"
                )
            )

            if failed > 0:
                _print_retry_hint(pdf_path, "process")

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted. Use --resume to continue later.[/yellow]")
        raise typer.Exit(130)


@app.command()
def fast(
    pdf_path: Path = typer.Argument(..., help="Path to the PDF file", exists=True),
    pages: str | None = typer.Option(
        None, "--pages", "-p", help="Page range (e.g., 'all', '1-50', '1,5,10-20')"
    ),
    resume: bool = typer.Option(False, "--resume", "-r", help="Resume from previous progress"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be processed"),
    model: str = typer.Option("gemini-2.0-flash", "--model", "-m", help="Gemini model to use"),
    dpi: int = typer.Option(200, "--dpi", help="DPI for PDF to image conversion"),
    workers: int = typer.Option(10, "--workers", "-w", help="Concurrent API workers (1-20)", min=1, max=20),
    rpm: int = typer.Option(60, "--rpm", help="Rate limit: requests per minute", min=10, max=120),
) -> None:
    """FAST: High-performance async OCR with concurrent workers.

    Uses parallel processing for 10-20x speedup over sequential mode.
    Recommended for processing large PDFs.

    Example::

        python -m ocr_hindi fast book.pdf --pages "1-100" --workers 10
    """
    console.print(
        Panel.fit(
            f"[bold cyan]OCR Hindi - FAST Mode[/bold cyan]\n"
            f"[dim]{pdf_path.name}[/dim]\n"
            f"[green]{workers} concurrent workers @ {rpm} RPM[/green]"
        )
    )

    total_pages = _get_pdf_pages(pdf_path)
    console.print(f"\n[bold]PDF Info:[/bold]")
    console.print(f"  Total pages: {total_pages}")

    page_list = _resolve_page_list(pages, total_pages)
    console.print(f"  Pages to process: {len(page_list)}")

    effective_rate = min(workers * 12, rpm)
    estimated_minutes = len(page_list) / effective_rate
    console.print(f"  Estimated time: ~{estimated_minutes:.1f} minutes")

    config = AsyncOCRConfig(
        model=model, dpi=dpi, max_concurrent=workers, requests_per_minute=rpm
    )
    processor = AsyncOCRProcessor(config=config)

    console.print("\n[bold]Validating authentication...[/bold]")
    success, auth_method, message = processor.validate_auth()

    if not success:
        console.print(f"[red]Authentication failed: {message}[/red]")
        console.print("Run 'python -m ocr_hindi validate' for help")
        raise typer.Exit(1)

    console.print(f"  [green]\u2713[/green] {auth_method}: {message}")

    def handle_interrupt(signum, frame):
        console.print(
            "\n[yellow]Interrupt received, shutting down gracefully...[/yellow]"
        )
        processor.request_shutdown()

    signal.signal(signal.SIGINT, handle_interrupt)

    try:
        successful, failed, output_path = asyncio.run(
            processor.process_pdf(
                pdf_path, page_list, resume=resume, dry_run=dry_run
            )
        )

        if not dry_run:
            console.print("\n")
            console.print(
                Panel.fit(
                    f"[green bold]\u2713 OCR Complete![/green bold]\n\n"
                    f"Processed: {successful} pages\n"
                    f"Failed: {failed} pages\n"
                    f"Output: {output_path}"
                )
            )

            if failed > 0:
                _print_retry_hint(pdf_path, "fast")

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted. Use --resume to continue later.[/yellow]")
        raise typer.Exit(130)


@app.command()
def ocr(
    pdf_path: Path = typer.Argument(..., help="Path to the PDF file", exists=True),
    pages: str | None = typer.Option(None, "--pages", "-p", help="Page range"),
    engine: str = typer.Option("hybrid", "--engine", "-e", help="OCR engine"),
    resume: bool = typer.Option(False, "--resume", "-r", help="Resume from previous progress"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be processed"),
    confidence: float = typer.Option(0.85, "--confidence", "-c", help="Confidence threshold", min=0.0, max=1.0),
    verify_mantras: bool = typer.Option(True, "--verify-mantras/--no-verify-mantras", help="Verify mantras with Gemini"),
    dpi: int = typer.Option(200, "--dpi", help="DPI for PDF to image conversion"),
    workers: int = typer.Option(5, "--workers", "-w", help="Concurrent workers (1-20)", min=1, max=20),
    batch: bool = typer.Option(False, "--batch", help="Use Vertex AI Batch API (50% savings)"),
    gcs_bucket: str | None = typer.Option(None, "--gcs-bucket", help="GCS bucket for batch API"),
    output_dir: Path | None = typer.Option(None, "--output-dir", "-o", help="Output directory"),
) -> None:
    """OCR with multiple backend support for cost optimization.

    ENGINES:

    - hybrid (default): EasyOCR + Gemini verification. 90%+ cost savings.

    - easyocr: FREE local OCR with good Hindi/Devanagari support.

    - marker: FREE local PDF to Markdown conversion.

    - tesseract: FREE Google's open-source OCR engine.

    - gemini: Original Gemini Vision API (expensive but accurate).

    EXAMPLES::

        python -m ocr_hindi ocr book.pdf --pages "all"
        python -m ocr_hindi ocr book.pdf -e easyocr --pages "1-100"
        python -m ocr_hindi ocr book.pdf -e gemini
    """
    engine_lower = engine.lower()
    if engine_lower not in _VALID_ENGINES:
        console.print(f"[red]Invalid engine: {engine}[/red]")
        console.print(f"Valid options: {', '.join(_VALID_ENGINES)}")
        raise typer.Exit(1)

    info = _ENGINE_INFO[engine_lower]
    total_pages = _get_pdf_pages(pdf_path)

    console.print()
    console.print(
        Panel(
            f"[bold white]{pdf_path.name}[/bold white]\n"
            f"[dim]Pages: {total_pages}[/dim]",
            title="[bold cyan]OCR Hindi[/bold cyan]",
            subtitle=info["badge"],
            border_style="cyan",
        )
    )

    config_table = Table(show_header=False, box=None, padding=(0, 2))
    config_table.add_column("Key", style="dim")
    config_table.add_column("Value", style="bold")
    config_table.add_row("Engine", engine_lower.upper())
    config_table.add_row("Model", info["model"])
    config_table.add_row("Cost", f"[green]{info['cost']}[/green]")
    if engine_lower == "hybrid":
        config_table.add_row("Threshold", f"{confidence:.0%}")
    console.print(config_table)

    page_list = _resolve_page_list(pages, total_pages)
    console.print(
        f"[dim]Processing {len(page_list)} of {total_pages} pages...[/dim]"
    )

    # Batch API mode
    if batch:
        _run_batch(pdf_path, page_list, engine_lower, info, dpi, gcs_bucket, output_dir)
        return

    # Standard mode
    config = MultiProcessorConfig(
        backend=engine_lower,
        dpi=dpi,
        max_concurrent=workers,
        confidence_threshold=confidence,
        detect_mantras=verify_mantras,
    )

    processor = MultiBackendProcessor(config=config)
    success, backend_name, message = processor.initialize(quiet=True)

    if not success:
        console.print(f"[red]Initialization failed: {message}[/red]")
        raise typer.Exit(1)

    try:
        if workers > 1 and engine_lower != "marker":
            successful, failed, output_path = asyncio.run(
                processor.process_pdf_async(
                    pdf_path, page_list,
                    resume=resume, dry_run=dry_run, output_dir=output_dir,
                )
            )
        else:
            successful, failed, output_path = processor.process_pdf(
                pdf_path, page_list,
                resume=resume, dry_run=dry_run, output_dir=output_dir,
            )

        if not dry_run:
            console.print("\n")
            console.print(
                Panel.fit(
                    f"[green bold]\u2713 OCR Complete![/green bold]\n\n"
                    f"Engine: {backend_name}\n"
                    f"Processed: {successful} pages\n"
                    f"Failed: {failed} pages\n"
                    f"Output: {output_path}"
                )
            )

            if failed > 0:
                _print_retry_hint(pdf_path, "ocr", engine_lower)

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted. Use --resume to continue later.[/yellow]")
        raise typer.Exit(130)

    finally:
        processor.cleanup()


def _run_batch(
    pdf_path: Path,
    page_list: list[int],
    engine: str,
    info: dict[str, str],
    dpi: int,
    gcs_bucket: str | None,
    output_dir: Path | None,
) -> None:
    """Run batch API processing mode.

    Args:
        pdf_path: Path to the PDF file.
        page_list: Resolved list of page numbers.
        engine: Engine name.
        info: Engine info dict.
        dpi: DPI for image conversion.
        gcs_bucket: GCS bucket name.
        output_dir: Output directory.
    """
    from .batch_processor import BatchConfig, BatchProcessor

    model_name = info.get("model", "gemini-2.0-flash").split()[-1]
    batch_config = BatchConfig(
        model=model_name,
        gcs_bucket=gcs_bucket or "",
        dpi=dpi,
    )
    batch_proc = BatchProcessor(batch_config)

    success_flag, msg = batch_proc.validate()
    if not success_flag:
        console.print(f"[red]Batch validation failed: {msg}[/red]")
        raise typer.Exit(1)

    console.print(f"[green]Batch API: {msg}[/green]")

    def on_progress(status: str) -> None:
        console.print(f"  [dim]{status}[/dim]")

    result = batch_proc.process_batch(pdf_path, page_list, on_progress=on_progress)

    if result.results:
        batch_output_dir = output_dir or (pdf_path.parent / f"{pdf_path.stem}_output")
        batch_output_dir = Path(batch_output_dir)
        batch_output_dir.mkdir(parents=True, exist_ok=True)
        output_file = batch_output_dir / f"{pdf_path.stem}_unicode.md"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sorted_pages = sorted(result.results.keys())

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"# {pdf_path.stem} - OCR Output\n")
            f.write(f"Generated: {timestamp}\n")
            f.write(f"Backend: Vertex AI Batch ({model_name})\n")
            f.write(f"Pages processed: {len(sorted_pages)}\n\n")
            f.write("---\n\n")
            for pg in sorted_pages:
                f.write(f"## Page {pg}\n\n")
                f.write(result.results[pg])
                f.write("\n\n---\n\n")

        meta = {
            "pdf_path": str(pdf_path),
            "total_pages": len(page_list),
            "ocr_pages": result.successful,
            "model_used": model_name,
            "cost": result.cost_estimate,
            "processed_at": timestamp,
            "batch_mode": True,
            "duration_seconds": result.duration_seconds,
        }
        meta_file = batch_output_dir / "metadata.json"
        meta_file.write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        output_display: Path | str = output_file
    else:
        output_display = "No results"

    console.print(
        Panel.fit(
            f"[green bold]\u2713 Batch OCR Complete![/green bold]\n\n"
            f"Processed: {result.successful} pages\n"
            f"Failed: {result.failed} pages\n"
            f"Cost estimate: ${result.cost_estimate:.4f}\n"
            f"Duration: {result.duration_seconds:.0f}s\n"
            f"Output: {output_display}"
        )
    )


@app.command()
def engines() -> None:
    """List available OCR engines and their features."""
    table = Table(title="Available OCR Engines")
    table.add_column("Engine", style="cyan", no_wrap=True)
    table.add_column("Cost", style="green")
    table.add_column("Accuracy", style="yellow")
    table.add_column("Best For", style="white")

    table.add_row(
        "hybrid (default)", "~$1/1000 pages", "High",
        "Best balance of cost and accuracy. Uses EasyOCR + Gemini verification.",
    )
    table.add_row(
        "easyocr", "FREE", "Good",
        "Local processing, good Hindi support. No API costs.",
    )
    table.add_row(
        "marker", "FREE", "Very Good",
        "Structured documents, books. Native Markdown output.",
    )
    table.add_row(
        "tesseract", "FREE", "Moderate",
        "Simple documents. Requires system install.",
    )
    table.add_row(
        "gemini", "~$10/1000 pages", "Excellent",
        "Complex manuscripts, when accuracy is critical.",
    )

    console.print("\n")
    console.print(table)

    console.print("\n[bold]Usage Examples:[/bold]")
    console.print("  # Hybrid mode (recommended)")
    console.print("  python -m ocr_hindi ocr book.pdf --pages all")
    console.print("")
    console.print("  # Free local processing")
    console.print("  python -m ocr_hindi ocr book.pdf -e easyocr")
    console.print("")
    console.print("  # Original Gemini (expensive)")
    console.print("  python -m ocr_hindi ocr book.pdf -e gemini")


@app.command()
def info(
    pdf_path: Path = typer.Argument(..., help="Path to the PDF file", exists=True),
) -> None:
    """Show PDF information."""
    try:
        pdf_info = pdfinfo_from_path(str(pdf_path))
    except Exception as exc:
        console.print(f"[red]Error reading PDF: {exc}[/red]")
        raise typer.Exit(1) from exc

    table = Table(title=f"PDF Info: {pdf_path.name}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    for key, value in pdf_info.items():
        table.add_row(str(key), str(value))

    console.print(table)


@app.command()
def benchmark(
    pdf_path: Path = typer.Argument(..., help="Path to the PDF file", exists=True),
    sample_pages: int = typer.Option(5, "--sample", "-s", help="Number of pages to benchmark"),
) -> None:
    """Benchmark OCR performance to find optimal settings.

    Tests different worker counts and reports throughput.
    """
    import time as time_mod

    console.print(Panel.fit("[bold]OCR Hindi - Benchmark[/bold]"))

    total_pages = _get_pdf_pages(pdf_path)
    test_pages = list(range(1, min(sample_pages + 1, total_pages + 1)))
    console.print(f"Testing with pages: {test_pages}")

    results: list[tuple[int, float, float]] = []

    for worker_count in [1, 5, 10]:
        console.print(f"\n[cyan]Testing {worker_count} workers...[/cyan]")

        config = AsyncOCRConfig(
            model="gemini-2.0-flash",
            max_concurrent=worker_count,
            requests_per_minute=60,
        )

        proc = AsyncOCRProcessor(config=config)
        success, _, _ = proc.validate_auth()

        if not success:
            console.print("[red]Auth failed[/red]")
            raise typer.Exit(1)

        start = time_mod.monotonic()

        try:
            successful, _, _ = asyncio.run(
                proc.process_pdf(pdf_path, test_pages, resume=False)
            )
            elapsed = time_mod.monotonic() - start
            pages_per_min = (successful / elapsed) * 60

            results.append((worker_count, elapsed, pages_per_min))
            console.print(
                f"  {successful} pages in {elapsed:.1f}s "
                f"({pages_per_min:.1f} pages/min)"
            )
        except Exception as exc:
            console.print(f"  [red]Error: {exc}[/red]")

    console.print("\n[bold]Benchmark Results:[/bold]")
    result_table = Table()
    result_table.add_column("Workers", style="cyan")
    result_table.add_column("Time", style="yellow")
    result_table.add_column("Throughput", style="green")

    for worker_count, elapsed, ppm in results:
        result_table.add_row(str(worker_count), f"{elapsed:.1f}s", f"{ppm:.1f} pages/min")

    console.print(result_table)

    if results:
        best = max(results, key=lambda x: x[2])
        console.print(
            f"\n[green]Optimal: {best[0]} workers ({best[2]:.1f} pages/min)[/green]"
        )
        full_time = total_pages / best[2]
        console.print(
            f"Estimated time for {total_pages} pages: "
            f"{format_duration(full_time * 60)}"
        )


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query (supports Devanagari)"),
    folder: Path = typer.Option(..., "--folder", "-f", help="OCR output folder", exists=True),
    book: str | None = typer.Option(None, "--book", "-b", help="Filter to a specific book"),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum results"),
) -> None:
    """Search across all OCR'd books using full-text search.

    Examples::

        ocr-hindi search "कुण्डलिनी" --folder /path/to/ocr_output/
        ocr-hindi search "mantra" -f ./ocr_tantra/ --book Goraksha_5
    """
    from .search import SearchIndex

    index = SearchIndex(folder)

    stats = index.get_stats()
    if not stats.get("indexed"):
        console.print("[yellow]Building search index...[/yellow]")
        pages_indexed = index.build()
        if pages_indexed == 0:
            console.print("[red]No OCR output files found to index.[/red]")
            raise typer.Exit(1)
        console.print(f"[green]Indexed {pages_indexed} pages[/green]")

    results = index.search(query, book_filter=book, limit=limit)

    if not results.has_results:
        console.print(f"[yellow]No results found for: {query}[/yellow]")
        raise typer.Exit(0)

    console.print(
        f"\n[bold]Found {results.total_count} results "
        f"in {results.books_matched} books:[/bold]\n"
    )

    for r in results.results:
        console.print(f"  [cyan]{r.book_name}[/cyan] - Page {r.page_num}")
        console.print(f"  [dim]{r.snippet}[/dim]")
        console.print()

    index.close()


@app.command()
def reindex(
    folder: Path = typer.Argument(..., help="OCR output folder", exists=True),
    force: bool = typer.Option(False, "--force", help="Force full rebuild"),
) -> None:
    """Build or rebuild the full-text search index.

    Scans the OCR output folder for ``*_unicode.md`` files and indexes
    their content for fast search.

    Examples::

        ocr-hindi reindex /path/to/ocr_output/
        ocr-hindi reindex ./ocr_tantra/ --force
    """
    from .search import SearchIndex

    index = SearchIndex(folder)

    console.print(
        f"[bold]{'Rebuilding' if force else 'Building'} search index...[/bold]"
    )
    console.print(f"  Folder: {folder}")

    pages_indexed = index.build(force=force)

    if pages_indexed == 0:
        console.print("[yellow]No OCR output files found to index.[/yellow]")
        raise typer.Exit(1)

    stats = index.get_stats()
    result_table = Table(title="Search Index")
    result_table.add_column("Property", style="cyan")
    result_table.add_column("Value", style="green")
    result_table.add_row("Pages indexed", str(pages_indexed))
    result_table.add_row("Books", str(stats.get("books", 0)))
    result_table.add_row("Index size", f"{stats.get('db_size_mb', 0):.1f} MB")
    result_table.add_row("Location", str(folder / "_search_index.db"))

    console.print(result_table)
    console.print("[green]Search index ready![/green]")

    index.close()


@app.command()
def ui() -> None:
    """Launch the Streamlit web UI."""
    try:
        import streamlit  # noqa: F401
    except ImportError:
        console.print("[red]Streamlit not installed. Install with:[/red]")
        console.print("  pip install 'ocr-devnagari[streamlit]'")
        raise typer.Exit(1)

    from .app_launcher import main as launch_ui

    launch_ui()


if __name__ == "__main__":
    app()
