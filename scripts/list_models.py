#!/usr/bin/env python3
"""Utility script to list available Leonardo AI models."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from leonardo import LeonardoClient
from leonardo.exceptions import LeonardoAuthError

app = typer.Typer(help="List available Leonardo AI models")
console = Console()

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")


@app.command()
def list_models(
    show_nsfw: bool = typer.Option(
        False,
        "--nsfw",
        help="Include NSFW models in the list",
    ),
    featured_only: bool = typer.Option(
        False,
        "--featured",
        help="Show only featured models",
    ),
    search: str = typer.Option(
        None,
        "--search", "-s",
        help="Search models by name",
    ),
) -> None:
    """List all available Leonardo AI platform models."""
    api_key = os.getenv("LEONARDO_API_KEY")
    if not api_key:
        console.print("[red]Error:[/red] LEONARDO_API_KEY not set in environment")
        raise typer.Exit(1)

    client = LeonardoClient(api_key)

    try:
        user = client.verify_api_key()
        console.print(f"[green]Authenticated as:[/green] {user.username or user.id}")
        if user.apiCredit is not None:
            console.print(f"[dim]API credits: {user.apiCredit}[/dim]\n")
    except LeonardoAuthError as e:
        console.print(f"[red]Authentication failed:[/red] {e}")
        raise typer.Exit(1)

    console.print("Fetching models...\n")
    models = client.list_models()

    # Filter models
    if not show_nsfw:
        models = [m for m in models if not m.nsfw]
    if featured_only:
        models = [m for m in models if m.featured]
    if search:
        search_lower = search.lower()
        models = [m for m in models if search_lower in m.name.lower()]

    if not models:
        console.print("[yellow]No models found matching criteria[/yellow]")
        return

    # Create table
    table = Table(title="Available Leonardo Models", show_lines=True)
    table.add_column("Model ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Description", max_width=50)
    table.add_column("Featured", justify="center")

    for model in sorted(models, key=lambda m: (not m.featured, m.name)):
        featured = "✓" if model.featured else ""
        description = (model.description or "")[:100]
        if len(model.description or "") > 100:
            description += "..."
        table.add_row(model.id, model.name, description, featured)

    console.print(table)
    console.print(f"\n[dim]Total models: {len(models)}[/dim]")
    console.print("\n[bold]To use a model, set MODEL_ID in your .env file:[/bold]")
    console.print("[dim]MODEL_ID=<model_id>[/dim]")

    client.close()


@app.command()
def info(
    model_id: str = typer.Argument(
        ...,
        help="Model ID to get info for",
    ),
) -> None:
    """Get detailed information about a specific model."""
    api_key = os.getenv("LEONARDO_API_KEY")
    if not api_key:
        console.print("[red]Error:[/red] LEONARDO_API_KEY not set in environment")
        raise typer.Exit(1)

    client = LeonardoClient(api_key)

    try:
        models = client.list_models()
        model = next((m for m in models if m.id == model_id), None)

        if not model:
            console.print(f"[red]Model not found:[/red] {model_id}")
            raise typer.Exit(1)

        console.print(f"\n[bold]{model.name}[/bold]")
        console.print(f"ID: {model.id}")
        console.print(f"Featured: {'Yes' if model.featured else 'No'}")
        console.print(f"NSFW: {'Yes' if model.nsfw else 'No'}")
        if model.description:
            console.print(f"\nDescription:\n{model.description}")

    finally:
        client.close()


if __name__ == "__main__":
    app()
