"""
CLI interface for Hindi/Sanskrit PDF OCR with multiple backend support.

Backends available:
- gemini: Original Gemini Vision API (accurate but expensive)
- marker: Open-source PDF to Markdown (FREE)
- easyocr: Open-source OCR with Hindi support (FREE)
- tesseract: Google's open-source OCR (FREE)
- hybrid: EasyOCR + Gemini verification (90%+ savings)
"""

import asyncio
import signal
import sys
from pathlib import Path
from typing import Optional

import typer
from pdf2image import pdfinfo_from_path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .async_processor import AsyncOCRConfig, AsyncOCRProcessor
from .processor import OCRConfig, OCRProcessor
from .multi_processor import MultiBackendProcessor, MultiProcessorConfig
from .utils import estimate_processing_time, format_duration, parse_page_range

app = typer.Typer(
    name="ocr-hindi",
    help="OCR tool for Hindi/Sanskrit PDFs using Gemini + Vertex AI",
    add_completion=False,
)
console = Console()


def version_callback(value: bool):
    if value:
        console.print(f"ocr-hindi version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
):
    """OCR tool for Hindi/Sanskrit PDFs using Gemini + Vertex AI"""
    pass


@app.command()
def validate():
    """Validate authentication and dependencies"""
    console.print(Panel.fit("[bold]OCR Hindi - Validation[/bold]"))

    # Check dependencies
    console.print("\n[bold]Checking dependencies...[/bold]")
    deps_ok = True

    try:
        import google.genai

        console.print("  [green]\u2713[/green] google-genai")
    except ImportError:
        console.print("  [red]\u2717[/red] google-genai (not installed)")
        deps_ok = False

    try:
        from pdf2image import convert_from_path

        console.print("  [green]\u2713[/green] pdf2image")
    except ImportError:
        console.print("  [red]\u2717[/red] pdf2image (not installed)")
        deps_ok = False

    try:
        from PIL import Image

        console.print("  [green]\u2713[/green] pillow")
    except ImportError:
        console.print("  [red]\u2717[/red] pillow (not installed)")
        deps_ok = False

    # Check poppler (required by pdf2image)
    try:
        import subprocess

        result = subprocess.run(
            ["pdftoppm", "-v"], capture_output=True, text=True, timeout=5
        )
        console.print("  [green]\u2713[/green] poppler (pdftoppm)")
    except (subprocess.SubprocessError, FileNotFoundError):
        console.print(
            "  [red]\u2717[/red] poppler (required by pdf2image). Install with: brew install poppler"
        )
        deps_ok = False

    if not deps_ok:
        console.print("\n[red]Dependencies missing. Install with:[/red]")
        console.print("  uv pip install -r requirements.txt")
        console.print("  brew install poppler")
        raise typer.Exit(1)

    # Check authentication
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
    pages: Optional[str] = typer.Option(
        None,
        "--pages",
        "-p",
        help="Page range (e.g., 'all', '1-50', '1,5,10-20')",
    ),
    resume: bool = typer.Option(
        False,
        "--resume",
        "-r",
        help="Resume from previous progress",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Show what would be processed without doing it",
    ),
    model: str = typer.Option(
        "gemini-3-flash-preview",
        "--model",
        "-m",
        help="Gemini model to use",
    ),
    dpi: int = typer.Option(
        200,
        "--dpi",
        help="DPI for PDF to image conversion",
    ),
):
    """Process a PDF file and extract text using OCR"""
    console.print(Panel.fit(f"[bold]OCR Hindi - Processing[/bold]\n{pdf_path.name}"))

    # Get PDF info
    try:
        pdf_info = pdfinfo_from_path(str(pdf_path))
        total_pages = pdf_info["Pages"]
    except Exception as e:
        console.print(f"[red]Error reading PDF: {e}[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]PDF Info:[/bold]")
    console.print(f"  Total pages: {total_pages}")

    # Parse or prompt for page range
    if pages is None:
        pages = typer.prompt(
            "Enter page range (e.g., all, 1-50, 1,5,10-20)",
            default="all",
        )

    try:
        page_list = parse_page_range(pages, total_pages)
    except ValueError as e:
        console.print(f"[red]Invalid page range: {e}[/red]")
        raise typer.Exit(1)

    console.print(f"  Pages to process: {len(page_list)}")

    # Estimate time
    estimated_time = estimate_processing_time(len(page_list))
    console.print(f"  Estimated time: {estimated_time}")

    if not dry_run:
        # Validate auth first
        config = OCRConfig(model=model, dpi=dpi)
        processor = OCRProcessor(config=config)

        console.print("\n[bold]Validating authentication...[/bold]")
        success, auth_method, message = processor.validate_auth()

        if not success:
            console.print(f"[red]Authentication failed: {message}[/red]")
            console.print("Run 'python -m ocr_hindi validate' for help")
            raise typer.Exit(1)

        console.print(f"  [green]\u2713[/green] {auth_method}")

    # Process
    try:
        if dry_run:
            processor = OCRProcessor(config=OCRConfig(model=model, dpi=dpi))
            processor.client = True  # Fake client for dry run
            processor.process_pdf(pdf_path, page_list, resume=resume, dry_run=True)
        else:
            successful, failed, output_path = processor.process_pdf(
                pdf_path, page_list, resume=resume, dry_run=False
            )

            # Print summary
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
                from .utils import get_progress_file, ProgressState

                progress_file = get_progress_file(pdf_path)
                state = ProgressState.load(progress_file)
                if state and state.failed_pages:
                    failed_str = ",".join(str(p) for p in sorted(state.failed_pages))
                    console.print(
                        f"\n[yellow]To retry failed pages:[/yellow]\n"
                        f'  python -m ocr_hindi process {pdf_path} --pages "{failed_str}"'
                    )

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted. Use --resume to continue later.[/yellow]")
        raise typer.Exit(130)


@app.command()
def fast(
    pdf_path: Path = typer.Argument(..., help="Path to the PDF file", exists=True),
    pages: Optional[str] = typer.Option(
        None,
        "--pages",
        "-p",
        help="Page range (e.g., 'all', '1-50', '1,5,10-20')",
    ),
    resume: bool = typer.Option(
        False,
        "--resume",
        "-r",
        help="Resume from previous progress",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Show what would be processed without doing it",
    ),
    model: str = typer.Option(
        "gemini-3-flash-preview",
        "--model",
        "-m",
        help="Gemini model to use",
    ),
    dpi: int = typer.Option(
        200,
        "--dpi",
        help="DPI for PDF to image conversion",
    ),
    workers: int = typer.Option(
        10,
        "--workers",
        "-w",
        help="Number of concurrent API workers (1-20)",
        min=1,
        max=20,
    ),
    rpm: int = typer.Option(
        60,
        "--rpm",
        help="Rate limit: requests per minute (default: 60)",
        min=10,
        max=120,
    ),
):
    """
    FAST: High-performance async OCR with concurrent workers.

    Uses parallel processing for 10-20x speedup over sequential mode.
    Recommended for processing large PDFs.

    Example:
        python -m ocr_hindi fast book.pdf --pages "1-100" --workers 10
    """
    console.print(
        Panel.fit(
            f"[bold cyan]OCR Hindi - FAST Mode[/bold cyan]\n"
            f"[dim]{pdf_path.name}[/dim]\n"
            f"[green]{workers} concurrent workers @ {rpm} RPM[/green]"
        )
    )

    # Get PDF info
    try:
        pdf_info = pdfinfo_from_path(str(pdf_path))
        total_pages = pdf_info["Pages"]
    except Exception as e:
        console.print(f"[red]Error reading PDF: {e}[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]PDF Info:[/bold]")
    console.print(f"  Total pages: {total_pages}")

    # Parse or prompt for page range
    if pages is None:
        pages = typer.prompt(
            "Enter page range (e.g., all, 1-50, 1,5,10-20)",
            default="all",
        )

    try:
        page_list = parse_page_range(pages, total_pages)
    except ValueError as e:
        console.print(f"[red]Invalid page range: {e}[/red]")
        raise typer.Exit(1)

    console.print(f"  Pages to process: {len(page_list)}")

    # Estimate time with concurrency
    effective_rate = min(workers * 12, rpm)  # ~12 pages/min per worker
    estimated_minutes = len(page_list) / effective_rate
    console.print(f"  Estimated time: ~{estimated_minutes:.1f} minutes")

    # Configure async processor
    config = AsyncOCRConfig(
        model=model,
        dpi=dpi,
        max_concurrent=workers,
        requests_per_minute=rpm,
    )

    processor = AsyncOCRProcessor(config=config)

    # Validate auth
    console.print("\n[bold]Validating authentication...[/bold]")
    success, auth_method, message = processor.validate_auth()

    if not success:
        console.print(f"[red]Authentication failed: {message}[/red]")
        console.print("Run 'python -m ocr_hindi validate' for help")
        raise typer.Exit(1)

    console.print(f"  [green]\u2713[/green] {auth_method}: {message}")

    # Setup signal handler for graceful shutdown
    def handle_interrupt(signum, frame):
        console.print(
            "\n[yellow]Interrupt received, shutting down gracefully...[/yellow]"
        )
        processor.request_shutdown()

    signal.signal(signal.SIGINT, handle_interrupt)

    # Run async processor
    try:
        successful, failed, output_path = asyncio.run(
            processor.process_pdf(pdf_path, page_list, resume=resume, dry_run=dry_run)
        )

        if not dry_run:
            # Print summary
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
                from .utils import get_progress_file, ProgressState

                progress_file = get_progress_file(pdf_path)
                state = ProgressState.load(progress_file)
                if state and state.failed_pages:
                    failed_str = ",".join(str(p) for p in sorted(state.failed_pages))
                    console.print(
                        f"\n[yellow]To retry failed pages:[/yellow]\n"
                        f'  python -m ocr_hindi fast {pdf_path} --pages "{failed_str}"'
                    )

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted. Use --resume to continue later.[/yellow]")
        raise typer.Exit(130)


@app.command()
def ocr(
    pdf_path: Path = typer.Argument(..., help="Path to the PDF file", exists=True),
    pages: Optional[str] = typer.Option(
        None,
        "--pages",
        "-p",
        help="Page range (e.g., 'all', '1-50', '1,5,10-20')",
    ),
    engine: str = typer.Option(
        "hybrid",
        "--engine",
        "-e",
        help="OCR engine: gemini, marker, easyocr, tesseract, hybrid",
    ),
    resume: bool = typer.Option(
        False,
        "--resume",
        "-r",
        help="Resume from previous progress",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Show what would be processed without doing it",
    ),
    confidence: float = typer.Option(
        0.85,
        "--confidence",
        "-c",
        help="Confidence threshold for hybrid mode (0.0-1.0)",
        min=0.0,
        max=1.0,
    ),
    verify_mantras: bool = typer.Option(
        True,
        "--verify-mantras/--no-verify-mantras",
        help="Verify pages with mantras using Gemini (hybrid mode)",
    ),
    dpi: int = typer.Option(
        200,
        "--dpi",
        help="DPI for PDF to image conversion",
    ),
    workers: int = typer.Option(
        5,
        "--workers",
        "-w",
        help="Number of concurrent workers (1-20)",
        min=1,
        max=20,
    ),
):
    """
    OCR with multiple backend support for cost optimization.
    
    ENGINES:
    
    - hybrid (default): EasyOCR + Gemini verification. 90%+ cost savings.
      Only uses Gemini for low-confidence pages and mantras.
    
    - easyocr: FREE local OCR with good Hindi/Devanagari support.
    
    - marker: FREE local PDF to Markdown conversion.
    
    - tesseract: FREE Google's open-source OCR engine.
    
    - gemini: Original Gemini Vision API (expensive but accurate).
    
    EXAMPLES:
    
        # Cost-effective hybrid mode (default)
        python -m ocr_hindi ocr book.pdf --pages "all"
        
        # Free local processing with EasyOCR
        python -m ocr_hindi ocr book.pdf -e easyocr --pages "1-100"
        
        # Free with Marker (best for structured PDFs)
        python -m ocr_hindi ocr book.pdf -e marker
        
        # Original Gemini (expensive but most accurate)
        python -m ocr_hindi ocr book.pdf -e gemini
    """
    # Validate engine
    valid_engines = ["gemini", "marker", "easyocr", "tesseract", "hybrid"]
    if engine.lower() not in valid_engines:
        console.print(f"[red]Invalid engine: {engine}[/red]")
        console.print(f"Valid options: {', '.join(valid_engines)}")
        raise typer.Exit(1)
    
    # Suppress torch warnings
    import warnings
    warnings.filterwarnings("ignore", message=".*pin_memory.*")
    warnings.filterwarnings("ignore", category=UserWarning, module="torch")
    
    # Engine info with model details
    engine_info = {
        "gemini": {
            "model": "gemini-3-flash-preview",
            "cost": "~$2/1K pages",
            "badge": "[bold white on red] PREMIUM [/bold white on red]",
            "desc": "Maximum accuracy",
        },
        "hybrid": {
            "model": "EasyOCR + gemini-3-flash-preview",
            "cost": "~$0.30/1K pages",
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
    info = engine_info.get(engine.lower(), engine_info["hybrid"])
    
    # Get PDF info first
    try:
        pdf_info = pdfinfo_from_path(str(pdf_path))
        total_pages = pdf_info["Pages"]
    except Exception as e:
        console.print(f"[red]Error reading PDF: {e}[/red]")
        raise typer.Exit(1)
    
    # Beautiful header panel
    console.print()
    console.print(
        Panel(
            f"[bold white]📄 {pdf_path.name}[/bold white]\n"
            f"[dim]Pages: {total_pages}[/dim]",
            title="[bold cyan]🕉️ OCR Hindi[/bold cyan]",
            subtitle=info["badge"],
            border_style="cyan",
        )
    )
    
    # Configuration table
    config_table = Table(show_header=False, box=None, padding=(0, 2))
    config_table.add_column("Key", style="dim")
    config_table.add_column("Value", style="bold")
    config_table.add_row("🔧 Engine", f"{engine.upper()}")
    config_table.add_row("🤖 Model", info["model"])
    config_table.add_row("💰 Cost", f"[green]{info['cost']}[/green]")
    if engine.lower() == "hybrid":
        config_table.add_row("📊 Threshold", f"{confidence:.0%}")
    console.print(config_table)
    
    # Parse or prompt for page range
    if pages is None:
        pages = typer.prompt(
            "Enter page range (e.g., all, 1-50, 1,5,10-20)",
            default="all",
        )
    
    try:
        page_list = parse_page_range(pages, total_pages)
    except ValueError as e:
        console.print(f"[red]Invalid page range: {e}[/red]")
        raise typer.Exit(1)
    
    console.print(f"[dim]Processing {len(page_list)} of {total_pages} pages...[/dim]")
    
    # Configure processor
    config = MultiProcessorConfig(
        backend=engine.lower(),
        dpi=dpi,
        max_concurrent=workers,
        confidence_threshold=confidence,
        detect_mantras=verify_mantras,
    )
    
    processor = MultiBackendProcessor(config=config)
    
    # Initialize backend (quietly)
    success, backend_name, message = processor.initialize(quiet=True)
    
    if not success:
        console.print(f"[red]Initialization failed: {message}[/red]")
        raise typer.Exit(1)
    
    # Process
    try:
        if workers > 1 and engine.lower() not in ["marker"]:
            # Use async processing for parallelism
            successful, failed, output_path = asyncio.run(
                processor.process_pdf_async(pdf_path, page_list, resume=resume, dry_run=dry_run)
            )
        else:
            # Sequential processing
            successful, failed, output_path = processor.process_pdf(
                pdf_path, page_list, resume=resume, dry_run=dry_run
            )
        
        if not dry_run:
            console.print("\n")
            console.print(
                Panel.fit(
                    f"[green bold]✓ OCR Complete![/green bold]\n\n"
                    f"Engine: {backend_name}\n"
                    f"Processed: {successful} pages\n"
                    f"Failed: {failed} pages\n"
                    f"Output: {output_path}"
                )
            )
            
            if failed > 0:
                from .utils import get_progress_file, ProgressState
                
                progress_file = get_progress_file(pdf_path)
                state = ProgressState.load(progress_file)
                if state and state.failed_pages:
                    failed_str = ",".join(str(p) for p in sorted(state.failed_pages))
                    console.print(
                        f"\n[yellow]To retry failed pages:[/yellow]\n"
                        f'  python -m ocr_hindi ocr {pdf_path} -e {engine} --pages "{failed_str}"'
                    )
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted. Use --resume to continue later.[/yellow]")
        raise typer.Exit(130)
    
    finally:
        processor.cleanup()


@app.command()
def engines():
    """List available OCR engines and their features"""
    table = Table(title="Available OCR Engines")
    table.add_column("Engine", style="cyan", no_wrap=True)
    table.add_column("Cost", style="green")
    table.add_column("Accuracy", style="yellow")
    table.add_column("Best For", style="white")
    
    table.add_row(
        "hybrid (default)",
        "~$1/1000 pages",
        "High",
        "Best balance of cost and accuracy. Uses EasyOCR + Gemini verification."
    )
    table.add_row(
        "easyocr",
        "FREE",
        "Good",
        "Local processing, good Hindi support. No API costs."
    )
    table.add_row(
        "marker",
        "FREE",
        "Very Good",
        "Structured documents, books. Native Markdown output."
    )
    table.add_row(
        "tesseract",
        "FREE",
        "Moderate",
        "Simple documents. Requires system install."
    )
    table.add_row(
        "gemini",
        "~$10/1000 pages",
        "Excellent",
        "Complex manuscripts, when accuracy is critical."
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
):
    """Show PDF information"""
    try:
        pdf_info = pdfinfo_from_path(str(pdf_path))

        table = Table(title=f"PDF Info: {pdf_path.name}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        for key, value in pdf_info.items():
            table.add_row(str(key), str(value))

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error reading PDF: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def benchmark(
    pdf_path: Path = typer.Argument(..., help="Path to the PDF file", exists=True),
    sample_pages: int = typer.Option(
        5,
        "--sample",
        "-s",
        help="Number of pages to benchmark",
    ),
):
    """
    Benchmark OCR performance to find optimal settings.

    Tests different worker counts and reports throughput.
    """
    console.print(Panel.fit("[bold]OCR Hindi - Benchmark[/bold]"))

    try:
        pdf_info = pdfinfo_from_path(str(pdf_path))
        total_pages = pdf_info["Pages"]
    except Exception as e:
        console.print(f"[red]Error reading PDF: {e}[/red]")
        raise typer.Exit(1)

    # Use first N pages for benchmark
    test_pages = list(range(1, min(sample_pages + 1, total_pages + 1)))
    console.print(f"Testing with pages: {test_pages}")

    results = []

    for workers in [1, 5, 10]:
        console.print(f"\n[cyan]Testing {workers} workers...[/cyan]")

        config = AsyncOCRConfig(
            model="gemini-3-flash-preview",
            max_concurrent=workers,
            requests_per_minute=60,
        )

        processor = AsyncOCRProcessor(config=config)
        success, _, _ = processor.validate_auth()

        if not success:
            console.print("[red]Auth failed[/red]")
            raise typer.Exit(1)

        import time

        start = time.monotonic()

        try:
            successful, failed, _ = asyncio.run(
                processor.process_pdf(pdf_path, test_pages, resume=False)
            )
            elapsed = time.monotonic() - start
            pages_per_min = (successful / elapsed) * 60

            results.append((workers, elapsed, pages_per_min))
            console.print(
                f"  {successful} pages in {elapsed:.1f}s "
                f"({pages_per_min:.1f} pages/min)"
            )

        except Exception as e:
            console.print(f"  [red]Error: {e}[/red]")

    # Print summary
    console.print("\n[bold]Benchmark Results:[/bold]")
    table = Table()
    table.add_column("Workers", style="cyan")
    table.add_column("Time", style="yellow")
    table.add_column("Throughput", style="green")

    for workers, elapsed, ppm in results:
        table.add_row(
            str(workers),
            f"{elapsed:.1f}s",
            f"{ppm:.1f} pages/min",
        )

    console.print(table)

    if results:
        best = max(results, key=lambda x: x[2])
        console.print(
            f"\n[green]Optimal: {best[0]} workers " f"({best[2]:.1f} pages/min)[/green]"
        )

        # Project full book time
        full_time = total_pages / best[2]
        console.print(
            f"Estimated time for {total_pages} pages: "
            f"{format_duration(full_time * 60)}"
        )


if __name__ == "__main__":
    app()
