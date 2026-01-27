#!/usr/bin/env python3
"""Generate prompt variations for coloring book themes."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Generate prompt variations for coloring book themes")
console = Console()

# Default variation modifiers for different themes
THEME_MODIFIERS = {
    "mandala": [
        "with floral elements",
        "with geometric patterns",
        "with nature motifs",
        "with celestial symbols",
        "with paisley designs",
        "with tribal patterns",
        "with zen garden elements",
        "with lotus flowers",
        "with peacock feathers",
        "with butterfly wings",
    ],
    "animals": [
        "in zentangle style",
        "with floral decorations",
        "in tribal art style",
        "with geometric patterns",
        "in folk art style",
        "with paisley patterns",
        "surrounded by flowers",
        "in a forest scene",
        "with decorative borders",
        "in art nouveau style",
    ],
    "flowers": [
        "in a garden arrangement",
        "with butterflies",
        "in a vase composition",
        "as a wreath design",
        "with hummingbirds",
        "in art nouveau frame",
        "as a border pattern",
        "with bees and insects",
        "in a bouquet style",
        "with decorative leaves",
    ],
    "nature": [
        "with woodland creatures",
        "in a forest scene",
        "by a peaceful stream",
        "in a meadow setting",
        "with mountain backdrop",
        "in a garden scene",
        "with seasonal elements",
        "under starry sky",
        "at sunset scene",
        "in tropical setting",
    ],
    "abstract": [
        "with flowing curves",
        "with geometric shapes",
        "with spiral patterns",
        "with wave motifs",
        "with tessellation design",
        "with fractal elements",
        "with optical illusions",
        "with zentangle patterns",
        "with doodle elements",
        "with mosaic style",
    ],
    "fantasy": [
        "with dragons",
        "in a fairy tale scene",
        "with unicorns",
        "in enchanted forest",
        "with magical creatures",
        "in a castle setting",
        "with mermaids",
        "in a mythical landscape",
        "with phoenixes",
        "in a magical garden",
    ],
    "default": [
        "detailed version",
        "simplified version",
        "with border design",
        "corner composition",
        "full page design",
        "with decorative frame",
        "symmetrical design",
        "asymmetrical layout",
        "with background pattern",
        "isolated elements",
    ],
}


def generate_variations(
    base_prompt: str,
    theme: str | None = None,
    count: int = 10,
    custom_modifiers: list[str] | None = None,
) -> list[str]:
    """
    Generate prompt variations from a base prompt.

    Args:
        base_prompt: The base subject/prompt
        theme: Theme to use for modifiers (mandala, animals, flowers, etc.)
        count: Number of variations to generate
        custom_modifiers: Custom list of modifiers to use instead of theme

    Returns:
        List of prompt variations
    """
    if custom_modifiers:
        modifiers = custom_modifiers
    elif theme and theme in THEME_MODIFIERS:
        modifiers = THEME_MODIFIERS[theme]
    else:
        modifiers = THEME_MODIFIERS["default"]

    # Ensure we have enough modifiers
    while len(modifiers) < count:
        modifiers = modifiers + modifiers

    variations = []
    for i in range(count):
        modifier = modifiers[i % len(modifiers)]
        variation = f"{base_prompt} {modifier}"
        variations.append(variation)

    return variations


def save_variations(
    variations: list[str],
    output_path: Path,
    base_prompt: str,
    seeds_per_variation: int = 5,
) -> None:
    """Save variations to YAML file."""
    data = {
        "base_prompt": base_prompt,
        "seeds_per_variation": seeds_per_variation,
        "total_pages": len(variations) * seeds_per_variation,
        "variations": variations,
    }

    with open(output_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


@app.command()
def create(
    base_prompt: str = typer.Argument(
        ...,
        help="Base prompt/subject for variations",
    ),
    count: int = typer.Option(
        10,
        "--count", "-n",
        help="Number of variations to generate",
    ),
    theme: str = typer.Option(
        None,
        "--theme", "-t",
        help="Theme for modifiers: mandala, animals, flowers, nature, abstract, fantasy",
    ),
    seeds_per_variation: int = typer.Option(
        5,
        "--seeds", "-s",
        help="Number of seeds per variation (for total page count)",
    ),
    output: Path = typer.Option(
        None,
        "--output", "-o",
        help="Output YAML file path",
    ),
    preview: bool = typer.Option(
        True,
        "--preview/--no-preview",
        help="Show preview of variations",
    ),
) -> None:
    """Create prompt variations from a base prompt."""
    # Generate variations
    variations = generate_variations(base_prompt, theme, count)

    if preview:
        console.print(f"\n[bold]Prompt Variations for:[/bold] {base_prompt}")
        if theme:
            console.print(f"[dim]Theme: {theme}[/dim]")
        console.print()

        table = Table(show_header=True)
        table.add_column("#", style="dim", width=4)
        table.add_column("Variation")
        table.add_column("Seeds", justify="center", width=8)

        for i, var in enumerate(variations, 1):
            table.add_row(str(i), var, str(seeds_per_variation))

        console.print(table)
        console.print()
        console.print(f"[bold]Total pages:[/bold] {len(variations) * seeds_per_variation}")

    # Save if output specified
    if output:
        output = Path(output)
        save_variations(variations, output, base_prompt, seeds_per_variation)
        console.print(f"\n[green]Saved to:[/green] {output}")
    elif not preview:
        # Output to stdout as YAML if no file and no preview
        import yaml
        print(yaml.dump({"variations": variations}, default_flow_style=False))


@app.command()
def themes():
    """List available themes and their modifiers."""
    console.print("\n[bold]Available Themes[/bold]\n")

    for theme, modifiers in THEME_MODIFIERS.items():
        if theme == "default":
            continue

        console.print(f"[cyan]{theme}[/cyan]")
        for mod in modifiers[:5]:
            console.print(f"  - {mod}")
        if len(modifiers) > 5:
            console.print(f"  [dim]... and {len(modifiers) - 5} more[/dim]")
        console.print()


@app.command()
def expand(
    variations_file: Path = typer.Argument(
        ...,
        help="YAML file with variations to expand",
    ),
    base_seed: int = typer.Option(
        42,
        "--seed", "-s",
        help="Base seed for generation",
    ),
) -> None:
    """Expand variations file into full page list with seeds."""
    if not variations_file.exists():
        console.print(f"[red]Error:[/red] File not found: {variations_file}")
        raise typer.Exit(1)

    with open(variations_file) as f:
        data = yaml.safe_load(f)

    variations = data.get("variations", [])
    seeds_per = data.get("seeds_per_variation", 5)

    console.print(f"\n[bold]Page Generation Plan[/bold]")
    console.print(f"Variations: {len(variations)}")
    console.print(f"Seeds per variation: {seeds_per}")
    console.print(f"Total pages: {len(variations) * seeds_per}")
    console.print()

    table = Table(show_header=True)
    table.add_column("Page", style="dim", width=6)
    table.add_column("Prompt")
    table.add_column("Seed", justify="right", width=10)

    page = 1
    for var_idx, variation in enumerate(variations):
        for seed_offset in range(seeds_per):
            seed = base_seed + (var_idx * seeds_per) + seed_offset
            table.add_row(str(page), variation[:60] + "...", str(seed))
            page += 1

            # Limit display
            if page > 20:
                break
        if page > 20:
            break

    console.print(table)

    if len(variations) * seeds_per > 20:
        remaining = len(variations) * seeds_per - 20
        console.print(f"\n[dim]... and {remaining} more pages[/dim]")


@app.command()
def init(
    prompts_dir: Path = typer.Option(
        None,
        "--dir", "-d",
        help="Prompts directory path",
    ),
) -> None:
    """Initialize default variations file in prompts directory."""
    if prompts_dir is None:
        prompts_dir = Path(__file__).parent.parent / "prompts"

    prompts_dir.mkdir(parents=True, exist_ok=True)
    output_path = prompts_dir / "variations.yaml"

    if output_path.exists():
        console.print(f"[yellow]File already exists:[/yellow] {output_path}")
        if not typer.confirm("Overwrite?"):
            raise typer.Exit(0)

    # Create default variations
    data = {
        "base_prompt": "mandala",
        "seeds_per_variation": 5,
        "variations": THEME_MODIFIERS["mandala"],
    }

    with open(output_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    console.print(f"[green]Created:[/green] {output_path}")
    console.print("\nEdit this file to customize your variations.")


if __name__ == "__main__":
    app()
