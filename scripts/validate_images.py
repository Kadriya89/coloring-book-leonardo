#!/usr/bin/env python3
"""Image validation script for coloring book pages."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import NamedTuple

import typer
from dotenv import load_dotenv
from PIL import Image
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Validate generated coloring book images")
console = Console()

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")


class ValidationResult(NamedTuple):
    """Result of validating a single image."""

    path: Path
    valid: bool
    issues: list[str]
    width: int | None = None
    height: int | None = None
    is_grayscale: bool | None = None
    white_ratio: float | None = None


def check_image_dimensions(
    img: Image.Image,
    expected_width: int,
    expected_height: int,
    tolerance: float = 0.05,
) -> tuple[bool, str | None]:
    """Check if image has expected dimensions (with tolerance)."""
    width, height = img.size
    width_ok = abs(width - expected_width) / expected_width <= tolerance
    height_ok = abs(height - expected_height) / expected_height <= tolerance

    if width_ok and height_ok:
        return True, None

    return False, f"Expected ~{expected_width}x{expected_height}, got {width}x{height}"


def check_is_grayscale(img: Image.Image) -> tuple[bool, str | None]:
    """Check if image is grayscale (no color channels)."""
    if img.mode == "L":
        return True, None
    if img.mode == "1":
        return True, None
    if img.mode in ("RGB", "RGBA"):
        # Sample pixels to check for color
        pixels = list(img.getdata())
        sample_size = min(10000, len(pixels))
        step = max(1, len(pixels) // sample_size)

        for i in range(0, len(pixels), step):
            pixel = pixels[i]
            if len(pixel) >= 3:
                r, g, b = pixel[:3]
                # Allow small variations due to compression artifacts
                if max(abs(r - g), abs(g - b), abs(r - b)) > 10:
                    return False, "Image contains color (not grayscale)"

        return True, None

    return True, None


def check_white_background(
    img: Image.Image,
    min_white_ratio: float = 0.3,
    white_threshold: int = 240,
) -> tuple[bool, float, str | None]:
    """Check if image has predominantly white background."""
    grayscale = img.convert("L")
    pixels = list(grayscale.getdata())

    white_count = sum(1 for p in pixels if p >= white_threshold)
    white_ratio = white_count / len(pixels)

    if white_ratio >= min_white_ratio:
        return True, white_ratio, None

    return False, white_ratio, f"White ratio {white_ratio:.1%} below minimum {min_white_ratio:.1%}"


def check_has_content(
    img: Image.Image,
    black_threshold: int = 50,
    min_content_ratio: float = 0.01,
) -> tuple[bool, str | None]:
    """Check if image has sufficient black line content."""
    grayscale = img.convert("L")
    pixels = list(grayscale.getdata())

    dark_count = sum(1 for p in pixels if p <= black_threshold)
    content_ratio = dark_count / len(pixels)

    if content_ratio >= min_content_ratio:
        return True, None

    return False, f"Content ratio {content_ratio:.1%} below minimum {min_content_ratio:.1%}"


def check_file_integrity(path: Path) -> tuple[bool, str | None]:
    """Check if image file is valid and not corrupted."""
    try:
        with Image.open(path) as img:
            img.verify()
        # Re-open after verify (verify can corrupt the file object)
        with Image.open(path) as img:
            img.load()
        return True, None
    except Exception as e:
        return False, f"File corrupted or invalid: {e}"


def validate_image(
    path: Path,
    expected_width: int = 2550,
    expected_height: int = 3300,
) -> ValidationResult:
    """Validate a single image against all criteria."""
    issues = []

    # Check file integrity first
    ok, error = check_file_integrity(path)
    if not ok:
        return ValidationResult(
            path=path,
            valid=False,
            issues=[error],
        )

    try:
        with Image.open(path) as img:
            width, height = img.size

            # Check dimensions
            ok, error = check_image_dimensions(img, expected_width, expected_height)
            if not ok:
                issues.append(error)

            # Check grayscale
            is_grayscale = True
            ok, error = check_is_grayscale(img)
            if not ok:
                issues.append(error)
                is_grayscale = False

            # Check white background
            ok, white_ratio, error = check_white_background(img)
            if not ok:
                issues.append(error)

            # Check has content
            ok, error = check_has_content(img)
            if not ok:
                issues.append(error)

            return ValidationResult(
                path=path,
                valid=len(issues) == 0,
                issues=issues,
                width=width,
                height=height,
                is_grayscale=is_grayscale,
                white_ratio=white_ratio,
            )

    except Exception as e:
        return ValidationResult(
            path=path,
            valid=False,
            issues=[f"Error processing image: {e}"],
        )


@app.command()
def validate(
    input_dir: Path = typer.Argument(
        ...,
        help="Directory containing images to validate",
    ),
    expected_width: int = typer.Option(
        None,
        "--width", "-w",
        help="Expected image width in pixels",
    ),
    expected_height: int = typer.Option(
        None,
        "--height", "-h",
        help="Expected image height in pixels",
    ),
    pattern: str = typer.Option(
        "*.png",
        "--pattern", "-p",
        help="Glob pattern for image files",
    ),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Exit with error if any images fail validation",
    ),
    output: Path = typer.Option(
        None,
        "--output", "-o",
        help="Write validation report to file",
    ),
) -> None:
    """Validate coloring book images for print quality."""
    # Apply defaults from environment
    expected_width = expected_width or int(os.getenv("WIDTH_PX", "2550"))
    expected_height = expected_height or int(os.getenv("HEIGHT_PX", "3300"))

    input_dir = Path(input_dir)
    if not input_dir.exists():
        console.print(f"[red]Error:[/red] Directory not found: {input_dir}")
        raise typer.Exit(1)

    # Find image files
    image_files = sorted(input_dir.glob(pattern))

    if not image_files:
        console.print(f"[yellow]No images found matching pattern:[/yellow] {pattern}")
        return

    console.print(f"\n[bold]Validating {len(image_files)} images...[/bold]\n")
    console.print(f"Expected dimensions: {expected_width}x{expected_height}px")
    console.print()

    # Validate each image
    results = []
    for path in image_files:
        result = validate_image(path, expected_width, expected_height)
        results.append(result)

    # Separate passed and failed
    passed = [r for r in results if r.valid]
    failed = [r for r in results if not r.valid]

    # Create summary table
    table = Table(title="Validation Results")
    table.add_column("File", style="cyan")
    table.add_column("Status")
    table.add_column("Dimensions")
    table.add_column("White %")
    table.add_column("Issues", max_width=40)

    for result in results:
        status = "[green]PASS[/green]" if result.valid else "[red]FAIL[/red]"
        dims = f"{result.width}x{result.height}" if result.width else "N/A"
        white = f"{result.white_ratio:.1%}" if result.white_ratio else "N/A"
        issues = "; ".join(result.issues) if result.issues else ""

        table.add_row(result.path.name, status, dims, white, issues)

    console.print(table)

    # Summary
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"  [green]Passed:[/green] {len(passed)}")
    console.print(f"  [red]Failed:[/red] {len(failed)}")
    console.print(f"  Total: {len(results)}")

    # Write report if requested
    if output:
        report_lines = ["# Image Validation Report\n"]
        report_lines.append(f"Directory: {input_dir}\n")
        report_lines.append(f"Expected: {expected_width}x{expected_height}px\n\n")
        report_lines.append(f"## Summary\n")
        report_lines.append(f"- Passed: {len(passed)}\n")
        report_lines.append(f"- Failed: {len(failed)}\n\n")

        if failed:
            report_lines.append("## Failed Images\n")
            for r in failed:
                report_lines.append(f"\n### {r.path.name}\n")
                for issue in r.issues:
                    report_lines.append(f"- {issue}\n")

        output.write_text("".join(report_lines))
        console.print(f"\nReport written to: {output}")

    # Exit with error if strict mode and failures
    if strict and failed:
        raise typer.Exit(1)


@app.command()
def check(
    image_path: Path = typer.Argument(
        ...,
        help="Single image file to validate",
    ),
) -> None:
    """Validate a single image file."""
    if not image_path.exists():
        console.print(f"[red]Error:[/red] File not found: {image_path}")
        raise typer.Exit(1)

    expected_width = int(os.getenv("WIDTH_PX", "2550"))
    expected_height = int(os.getenv("HEIGHT_PX", "3300"))

    result = validate_image(image_path, expected_width, expected_height)

    if result.valid:
        console.print(f"[green]✓ VALID[/green]: {image_path.name}")
        console.print(f"  Dimensions: {result.width}x{result.height}")
        console.print(f"  White ratio: {result.white_ratio:.1%}")
        console.print(f"  Grayscale: {'Yes' if result.is_grayscale else 'No'}")
    else:
        console.print(f"[red]✗ INVALID[/red]: {image_path.name}")
        for issue in result.issues:
            console.print(f"  - {issue}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
