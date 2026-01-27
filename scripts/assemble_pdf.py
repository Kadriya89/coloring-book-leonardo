#!/usr/bin/env python3
"""PDF assembly script for coloring book pages."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Literal

import typer
from dotenv import load_dotenv
from PIL import Image
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

app = typer.Typer(help="Assemble coloring book images into PDF")
console = Console()

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

# Page sizes in points (72 points = 1 inch)
PAGE_SIZES = {
    "letter": letter,  # 8.5 x 11 inches
    "a4": A4,  # 210 x 297 mm
    "square8": (8 * inch, 8 * inch),
    "square10": (10 * inch, 10 * inch),
}


def get_image_files(
    input_dir: Path,
    pattern: str = "*.png",
    sort_key: Literal["name", "modified", "created"] = "name",
) -> list[Path]:
    """Get sorted list of image files from directory."""
    files = list(input_dir.glob(pattern))

    if sort_key == "name":
        files.sort(key=lambda p: p.name)
    elif sort_key == "modified":
        files.sort(key=lambda p: p.stat().st_mtime)
    elif sort_key == "created":
        files.sort(key=lambda p: p.stat().st_ctime)

    return files


def calculate_image_placement(
    page_width: float,
    page_height: float,
    img_width: int,
    img_height: int,
    margin: float = 0.5 * inch,
    bleed: float = 0,
) -> tuple[float, float, float, float]:
    """
    Calculate image placement to fit page with margins.

    Returns: (x, y, width, height) in points
    """
    # Available area after margins
    available_width = page_width - (2 * margin) + (2 * bleed)
    available_height = page_height - (2 * margin) + (2 * bleed)

    # Calculate scale to fit
    scale_x = available_width / img_width
    scale_y = available_height / img_height
    scale = min(scale_x, scale_y)

    # Final dimensions
    final_width = img_width * scale
    final_height = img_height * scale

    # Center on page
    x = (page_width - final_width) / 2
    y = (page_height - final_height) / 2

    return x, y, final_width, final_height


def add_page_number(
    c: canvas.Canvas,
    page_num: int,
    page_width: float,
    page_height: float,
    margin: float = 0.5 * inch,
) -> None:
    """Add page number to bottom center of page."""
    c.setFont("Helvetica", 10)
    text = str(page_num)
    text_width = c.stringWidth(text, "Helvetica", 10)
    x = (page_width - text_width) / 2
    y = margin / 2
    c.drawString(x, y, text)


def create_title_page(
    c: canvas.Canvas,
    title: str,
    subtitle: str | None,
    page_width: float,
    page_height: float,
) -> None:
    """Create a title page."""
    # Title
    c.setFont("Helvetica-Bold", 36)
    title_width = c.stringWidth(title, "Helvetica-Bold", 36)
    x = (page_width - title_width) / 2
    y = page_height * 0.6
    c.drawString(x, y, title)

    # Subtitle
    if subtitle:
        c.setFont("Helvetica", 18)
        subtitle_width = c.stringWidth(subtitle, "Helvetica", 18)
        x = (page_width - subtitle_width) / 2
        y = page_height * 0.5
        c.drawString(x, y, subtitle)

    c.showPage()


def create_toc_page(
    c: canvas.Canvas,
    page_count: int,
    page_width: float,
    page_height: float,
) -> None:
    """Create a table of contents page."""
    c.setFont("Helvetica-Bold", 24)
    title = "Contents"
    title_width = c.stringWidth(title, "Helvetica-Bold", 24)
    x = (page_width - title_width) / 2
    y = page_height - 1.5 * inch
    c.drawString(x, y, title)

    c.setFont("Helvetica", 12)
    y -= 0.5 * inch

    # List pages
    left_margin = 1.5 * inch
    for i in range(1, page_count + 1):
        if y < 1 * inch:
            c.showPage()
            c.setFont("Helvetica", 12)
            y = page_height - 1 * inch

        c.drawString(left_margin, y, f"Page {i}")
        y -= 0.3 * inch

    c.showPage()


@app.command()
def assemble(
    input_dir: Path = typer.Argument(
        ...,
        help="Directory containing images to assemble",
    ),
    output: Path = typer.Option(
        None,
        "--output", "-o",
        help="Output PDF file path",
    ),
    pattern: str = typer.Option(
        "*.png",
        "--pattern", "-p",
        help="Glob pattern for image files",
    ),
    page_size: str = typer.Option(
        "letter",
        "--page-size", "-s",
        help="Page size: letter, a4, square8, square10",
    ),
    margin: float = typer.Option(
        0.5,
        "--margin", "-m",
        help="Margin in inches",
    ),
    bleed: float = typer.Option(
        0.0,
        "--bleed", "-b",
        help="Bleed area in inches (for professional printing)",
    ),
    title: str = typer.Option(
        None,
        "--title", "-t",
        help="Book title for title page",
    ),
    subtitle: str = typer.Option(
        None,
        "--subtitle",
        help="Subtitle for title page",
    ),
    page_numbers: bool = typer.Option(
        False,
        "--page-numbers/--no-page-numbers",
        help="Add page numbers",
    ),
    toc: bool = typer.Option(
        False,
        "--toc",
        help="Include table of contents",
    ),
    quality: int = typer.Option(
        85,
        "--quality", "-q",
        help="JPEG quality for embedded images (1-100)",
    ),
    sort: str = typer.Option(
        "name",
        "--sort",
        help="Sort order: name, modified, created",
    ),
) -> None:
    """Assemble coloring book images into a single PDF."""
    input_dir = Path(input_dir)
    if not input_dir.exists():
        console.print(f"[red]Error:[/red] Directory not found: {input_dir}")
        raise typer.Exit(1)

    # Default output path
    if output is None:
        book_slug = os.getenv("BOOK_SLUG", "coloring_book")
        output = input_dir.parent / f"{book_slug}.pdf"

    output = Path(output)

    # Get page size
    if page_size.lower() not in PAGE_SIZES:
        console.print(f"[red]Error:[/red] Unknown page size: {page_size}")
        console.print(f"Available: {', '.join(PAGE_SIZES.keys())}")
        raise typer.Exit(1)

    page_width, page_height = PAGE_SIZES[page_size.lower()]
    margin_pts = margin * inch
    bleed_pts = bleed * inch

    # Find image files
    image_files = get_image_files(input_dir, pattern, sort)

    if not image_files:
        console.print(f"[yellow]No images found matching pattern:[/yellow] {pattern}")
        return

    console.print(f"\n[bold]Assembling PDF from {len(image_files)} images...[/bold]\n")
    console.print(f"Input: {input_dir}")
    console.print(f"Output: {output}")
    console.print(f"Page size: {page_size} ({page_width/inch:.1f}\" x {page_height/inch:.1f}\")")
    console.print(f"Margin: {margin}\"")
    if bleed > 0:
        console.print(f"Bleed: {bleed}\"")
    console.print()

    # Create PDF
    c = canvas.Canvas(str(output), pagesize=(page_width, page_height))

    # Title page
    if title:
        console.print("Adding title page...")
        create_title_page(c, title, subtitle, page_width, page_height)

    # Table of contents
    if toc:
        console.print("Adding table of contents...")
        create_toc_page(c, len(image_files), page_width, page_height)

    # Add pages
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Adding pages...", total=len(image_files))

        for i, img_path in enumerate(image_files, 1):
            try:
                with Image.open(img_path) as img:
                    img_width, img_height = img.size

                    # Calculate placement
                    x, y, w, h = calculate_image_placement(
                        page_width, page_height,
                        img_width, img_height,
                        margin_pts, bleed_pts,
                    )

                    # Draw image
                    c.drawImage(
                        str(img_path),
                        x, y, w, h,
                        preserveAspectRatio=True,
                    )

                    # Page number
                    if page_numbers:
                        add_page_number(c, i, page_width, page_height, margin_pts)

                    c.showPage()

            except Exception as e:
                console.print(f"[yellow]Warning:[/yellow] Failed to add {img_path.name}: {e}")

            progress.update(task, advance=1)

    # Save PDF
    c.save()

    # Get file size
    size_mb = output.stat().st_size / (1024 * 1024)

    console.print()
    console.print(f"[bold green]PDF created successfully![/bold green]")
    console.print(f"  File: {output}")
    console.print(f"  Size: {size_mb:.1f} MB")
    console.print(f"  Pages: {len(image_files)}")


@app.command()
def split(
    input_pdf: Path = typer.Argument(
        ...,
        help="PDF file to split into individual pages",
    ),
    output_dir: Path = typer.Option(
        None,
        "--output", "-o",
        help="Output directory for individual pages",
    ),
    format: str = typer.Option(
        "PNG",
        "--format", "-f",
        help="Output image format (PNG or JPEG)",
    ),
    dpi: int = typer.Option(
        300,
        "--dpi",
        help="Output resolution in DPI",
    ),
) -> None:
    """Split a PDF into individual image files."""
    console.print("[yellow]Note:[/yellow] PDF splitting requires pdf2image and poppler.")
    console.print("Install with: pip install pdf2image")
    console.print("And install poppler for your platform.")

    try:
        from pdf2image import convert_from_path
    except ImportError:
        console.print("[red]Error:[/red] pdf2image not installed")
        raise typer.Exit(1)

    if not input_pdf.exists():
        console.print(f"[red]Error:[/red] File not found: {input_pdf}")
        raise typer.Exit(1)

    output_dir = output_dir or input_pdf.parent / input_pdf.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"Splitting {input_pdf} at {dpi} DPI...")

    images = convert_from_path(input_pdf, dpi=dpi)

    for i, img in enumerate(images, 1):
        ext = format.lower()
        if ext == "jpeg":
            ext = "jpg"
        output_path = output_dir / f"page_{i:03d}.{ext}"
        img.save(output_path, format.upper())
        console.print(f"  Saved: {output_path.name}")

    console.print(f"\n[green]Split {len(images)} pages to {output_dir}[/green]")


if __name__ == "__main__":
    app()
