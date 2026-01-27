#!/usr/bin/env python3
"""Post-processing script for coloring book line art."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Literal

import typer
from dotenv import load_dotenv
from PIL import Image, ImageFilter, ImageOps
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

app = typer.Typer(help="Post-process coloring book images for print quality")
console = Console()

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")


def convert_to_bw(
    img: Image.Image,
    threshold: int = 128,
) -> Image.Image:
    """Convert image to pure black and white (1-bit)."""
    # Convert to grayscale first
    grayscale = img.convert("L")
    # Apply threshold to create binary image
    return grayscale.point(lambda x: 255 if x > threshold else 0, mode="1")


def convert_to_grayscale(img: Image.Image) -> Image.Image:
    """Convert image to grayscale."""
    return img.convert("L")


def remove_antialiasing(
    img: Image.Image,
    threshold: int = 200,
) -> Image.Image:
    """Remove gray anti-aliasing artifacts by thresholding."""
    grayscale = img.convert("L")
    # Two-level threshold: dark pixels become black, light become white
    return grayscale.point(lambda x: 255 if x > threshold else 0)


def enhance_contrast(
    img: Image.Image,
    factor: float = 1.5,
) -> Image.Image:
    """Enhance line contrast."""
    from PIL import ImageEnhance

    grayscale = img.convert("L")
    enhancer = ImageEnhance.Contrast(grayscale)
    return enhancer.enhance(factor)


def clean_margins(
    img: Image.Image,
    margin_percent: float = 2.0,
    white_value: int = 255,
) -> Image.Image:
    """Ensure clean white margins around the image."""
    width, height = img.size
    margin_x = int(width * margin_percent / 100)
    margin_y = int(height * margin_percent / 100)

    # Work with grayscale
    if img.mode != "L":
        result = img.convert("L")
    else:
        result = img.copy()

    # Create pixel access
    pixels = result.load()

    # Clean top margin
    for y in range(margin_y):
        for x in range(width):
            pixels[x, y] = white_value

    # Clean bottom margin
    for y in range(height - margin_y, height):
        for x in range(width):
            pixels[x, y] = white_value

    # Clean left margin
    for y in range(height):
        for x in range(margin_x):
            pixels[x, y] = white_value

    # Clean right margin
    for y in range(height):
        for x in range(width - margin_x, width):
            pixels[x, y] = white_value

    return result


def sharpen_lines(img: Image.Image) -> Image.Image:
    """Sharpen lines using unsharp mask."""
    grayscale = img.convert("L")
    return grayscale.filter(ImageFilter.SHARPEN)


def process_image(
    input_path: Path,
    output_path: Path,
    binarize: bool = False,
    threshold: int = 128,
    remove_aa: bool = False,
    aa_threshold: int = 200,
    contrast: float | None = None,
    clean_margin: float | None = None,
    sharpen: bool = False,
    output_format: str = "PNG",
) -> bool:
    """
    Process a single image with specified operations.

    Returns True if successful, False otherwise.
    """
    try:
        with Image.open(input_path) as img:
            result = img

            # Apply operations in order
            if sharpen:
                result = sharpen_lines(result)

            if contrast:
                result = enhance_contrast(result, contrast)

            if remove_aa:
                result = remove_antialiasing(result, aa_threshold)

            if binarize:
                result = convert_to_bw(result, threshold)
            else:
                # At minimum, convert to grayscale
                result = convert_to_grayscale(result)

            if clean_margin:
                result = clean_margins(result, clean_margin)

            # Save with appropriate settings
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if output_format.upper() == "PNG":
                result.save(output_path, "PNG", optimize=True)
            elif output_format.upper() in ("JPG", "JPEG"):
                # Convert 1-bit to L for JPEG
                if result.mode == "1":
                    result = result.convert("L")
                result.save(output_path, "JPEG", quality=95, optimize=True)
            else:
                result.save(output_path)

            return True

    except Exception as e:
        console.print(f"[red]Error processing {input_path.name}:[/red] {e}")
        return False


@app.command()
def process(
    input_dir: Path = typer.Argument(
        ...,
        help="Directory containing images to process",
    ),
    output_dir: Path = typer.Option(
        None,
        "--output", "-o",
        help="Output directory (default: input_dir/processed)",
    ),
    pattern: str = typer.Option(
        "*.png",
        "--pattern", "-p",
        help="Glob pattern for image files",
    ),
    binarize: bool = typer.Option(
        False,
        "--binarize", "-b",
        help="Convert to pure black and white (1-bit)",
    ),
    threshold: int = typer.Option(
        128,
        "--threshold", "-t",
        help="Binarization threshold (0-255)",
    ),
    remove_aa: bool = typer.Option(
        False,
        "--remove-aa",
        help="Remove anti-aliasing artifacts",
    ),
    aa_threshold: int = typer.Option(
        200,
        "--aa-threshold",
        help="Anti-aliasing removal threshold",
    ),
    contrast: float = typer.Option(
        None,
        "--contrast", "-c",
        help="Contrast enhancement factor (e.g., 1.5)",
    ),
    margin: float = typer.Option(
        None,
        "--margin", "-m",
        help="Clean margin percentage (e.g., 2.0 for 2%)",
    ),
    sharpen: bool = typer.Option(
        False,
        "--sharpen",
        help="Sharpen lines",
    ),
    format: str = typer.Option(
        "PNG",
        "--format", "-f",
        help="Output format (PNG or JPEG)",
    ),
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        help="Overwrite existing output files",
    ),
) -> None:
    """Post-process coloring book images for better print quality."""
    input_dir = Path(input_dir)
    if not input_dir.exists():
        console.print(f"[red]Error:[/red] Directory not found: {input_dir}")
        raise typer.Exit(1)

    output_dir = output_dir or input_dir / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find image files
    image_files = sorted(input_dir.glob(pattern))
    # Exclude already processed
    image_files = [f for f in image_files if "processed" not in str(f)]

    if not image_files:
        console.print(f"[yellow]No images found matching pattern:[/yellow] {pattern}")
        return

    console.print(f"\n[bold]Processing {len(image_files)} images...[/bold]\n")
    console.print(f"Input: {input_dir}")
    console.print(f"Output: {output_dir}")
    console.print()

    # Show settings
    settings = []
    if binarize:
        settings.append(f"Binarize (threshold={threshold})")
    if remove_aa:
        settings.append(f"Remove anti-aliasing (threshold={aa_threshold})")
    if contrast:
        settings.append(f"Enhance contrast ({contrast}x)")
    if margin:
        settings.append(f"Clean margins ({margin}%)")
    if sharpen:
        settings.append("Sharpen lines")

    if settings:
        console.print("[bold]Operations:[/bold]")
        for s in settings:
            console.print(f"  - {s}")
        console.print()

    # Process images
    success_count = 0
    fail_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Processing...", total=len(image_files))

        for input_path in image_files:
            # Determine output extension
            ext = format.lower()
            if ext == "jpeg":
                ext = "jpg"
            output_name = input_path.stem + "." + ext
            output_path = output_dir / output_name

            if output_path.exists() and not overwrite:
                success_count += 1
                progress.update(task, advance=1)
                continue

            if process_image(
                input_path=input_path,
                output_path=output_path,
                binarize=binarize,
                threshold=threshold,
                remove_aa=remove_aa,
                aa_threshold=aa_threshold,
                contrast=contrast,
                clean_margin=margin,
                sharpen=sharpen,
                output_format=format,
            ):
                success_count += 1
            else:
                fail_count += 1

            progress.update(task, advance=1)

    console.print()
    console.print(f"[bold]Processing complete![/bold]")
    console.print(f"  [green]Success:[/green] {success_count}")
    if fail_count:
        console.print(f"  [red]Failed:[/red] {fail_count}")
    console.print(f"\nOutput saved to: {output_dir}")


@app.command()
def preview(
    image_path: Path = typer.Argument(
        ...,
        help="Image file to preview processing on",
    ),
    binarize: bool = typer.Option(False, "--binarize", "-b"),
    threshold: int = typer.Option(128, "--threshold", "-t"),
    remove_aa: bool = typer.Option(False, "--remove-aa"),
    contrast: float = typer.Option(None, "--contrast", "-c"),
    sharpen: bool = typer.Option(False, "--sharpen"),
) -> None:
    """Preview processing on a single image (saves to temp file)."""
    if not image_path.exists():
        console.print(f"[red]Error:[/red] File not found: {image_path}")
        raise typer.Exit(1)

    # Create preview in temp location
    output_path = image_path.parent / f"preview_{image_path.name}"

    success = process_image(
        input_path=image_path,
        output_path=output_path,
        binarize=binarize,
        threshold=threshold,
        remove_aa=remove_aa,
        contrast=contrast,
        sharpen=sharpen,
    )

    if success:
        console.print(f"[green]Preview saved to:[/green] {output_path}")
    else:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
