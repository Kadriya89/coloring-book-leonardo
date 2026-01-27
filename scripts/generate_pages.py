#!/usr/bin/env python3
"""Main generation script for coloring book pages."""

from __future__ import annotations

import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

import typer
import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from leonardo import LeonardoClient
from leonardo.exceptions import LeonardoAPIError, LeonardoAuthError

app = typer.Typer(help="Generate coloring book pages using Leonardo AI")
console = Console()

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")


def setup_logging(level: str = "INFO") -> None:
    """Configure logging with rich handler."""
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, show_time=False)],
    )


def load_prompts(prompts_dir: Path) -> tuple[str, str]:
    """Load base and negative prompts from YAML files."""
    base_path = prompts_dir / "base_prompts.yaml"
    negative_path = prompts_dir / "negative_prompts.yaml"

    base_template = ""
    negative_prompt = ""

    if base_path.exists():
        with open(base_path) as f:
            data = yaml.safe_load(f)
            base_template = data.get("base_template", "")

    if negative_path.exists():
        with open(negative_path) as f:
            data = yaml.safe_load(f)
            negative_prompt = data.get("negative_prompt", "")

    return base_template, negative_prompt


def load_variations(prompts_dir: Path) -> list[str]:
    """Load prompt variations if available."""
    variations_path = prompts_dir / "variations.yaml"
    if variations_path.exists():
        with open(variations_path) as f:
            data = yaml.safe_load(f)
            return data.get("variations", [])
    return []


def generate_prompt(
    subject: str,
    base_template: str,
    variation: str | None = None,
) -> str:
    """Generate a full prompt from subject and template."""
    if variation:
        full_subject = f"{subject} {variation}"
    else:
        full_subject = subject

    if base_template and "{subject}" in base_template:
        return base_template.format(subject=full_subject)
    elif base_template:
        return f"{full_subject}, {base_template}"
    else:
        # Default coloring book style prompt
        return (
            f"{full_subject}, black and white line art, coloring book page style, "
            "clean outlines, no shading, no gradients, no fills, "
            "intricate details suitable for adult coloring, "
            "white background, crisp black lines"
        )


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    """Load existing manifest or create new one."""
    if manifest_path.exists():
        completed = {}
        with open(manifest_path) as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    completed[entry.get("page_num")] = entry
        return completed
    return {}


def append_to_manifest(manifest_path: Path, entry: dict) -> None:
    """Append a generation entry to the manifest."""
    with open(manifest_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def generate_single_page(
    client: LeonardoClient,
    page_num: int,
    prompt: str,
    negative_prompt: str,
    output_dir: Path,
    model_id: str | None,
    seed: int | None,
    width: int,
    height: int,
) -> dict:
    """Generate a single coloring book page."""
    try:
        gen_id = client.create_generation(
            prompt=prompt,
            model_id=model_id,
            width=width,
            height=height,
            seed=seed,
            negative_prompt=negative_prompt,
            num_images=1,
        )

        generation = client.poll_until_complete(gen_id)

        if not generation.generated_images:
            raise LeonardoAPIError("No images in completed generation")

        image = generation.generated_images[0]
        filename = f"page_{page_num:03d}.png"
        dest_path = output_dir / filename

        client.download_image(image.url, dest_path)

        return {
            "page_num": page_num,
            "status": "success",
            "generation_id": gen_id,
            "prompt": prompt,
            "seed": seed,
            "filename": filename,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        return {
            "page_num": page_num,
            "status": "failed",
            "error": str(e),
            "prompt": prompt,
            "seed": seed,
            "timestamp": datetime.now().isoformat(),
        }


@app.command()
def generate(
    prompt: str = typer.Option(
        ...,
        "--prompt", "-p",
        help="Base prompt/subject for the coloring book pages",
    ),
    pages: int = typer.Option(
        None,
        "--pages", "-n",
        help="Number of pages to generate (default: from .env PAGE_COUNT)",
    ),
    output_dir: Path = typer.Option(
        None,
        "--output-dir", "-o",
        help="Output directory for generated images",
    ),
    model_id: str = typer.Option(
        None,
        "--model-id", "-m",
        help="Leonardo model ID to use",
    ),
    seed: int = typer.Option(
        None,
        "--seed", "-s",
        help="Base seed for reproducibility",
    ),
    concurrency: int = typer.Option(
        None,
        "--concurrency", "-c",
        help="Number of concurrent generation requests",
    ),
    resume: bool = typer.Option(
        False,
        "--resume", "-r",
        help="Resume from previous run, skipping completed pages",
    ),
    use_variations: bool = typer.Option(
        True,
        "--variations/--no-variations",
        help="Use prompt variations for diversity",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be generated without making API calls",
    ),
) -> None:
    """Generate coloring book pages using Leonardo AI."""
    # Load config from environment
    api_key = os.getenv("LEONARDO_API_KEY")
    if not api_key:
        console.print("[red]Error:[/red] LEONARDO_API_KEY not set in environment")
        raise typer.Exit(1)

    # Apply defaults from environment
    pages = pages or int(os.getenv("PAGE_COUNT", "50"))
    base_output = Path(os.getenv("OUTPUT_DIR", "outputs"))
    book_slug = os.getenv("BOOK_SLUG", "coloring_book")
    output_dir = output_dir or base_output / book_slug
    model_id = model_id or os.getenv("MODEL_ID") or None
    seed = seed if seed is not None else int(os.getenv("DEFAULT_SEED", "42"))
    concurrency = concurrency or int(os.getenv("CONCURRENCY", "3"))
    width = int(os.getenv("WIDTH_PX", "2550"))
    height = int(os.getenv("HEIGHT_PX", "3300"))
    log_level = os.getenv("LOG_LEVEL", "INFO")

    setup_logging(log_level)
    logger = logging.getLogger(__name__)

    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load prompt templates
    prompts_dir = Path(__file__).parent.parent / "prompts"
    base_template, negative_prompt = load_prompts(prompts_dir)
    variations = load_variations(prompts_dir) if use_variations else []

    # Generate page configurations
    page_configs = []
    for i in range(pages):
        page_num = i + 1
        # Cycle through variations if available
        variation = variations[i % len(variations)] if variations else None
        page_seed = seed + i if seed is not None else None
        full_prompt = generate_prompt(prompt, base_template, variation)

        page_configs.append({
            "page_num": page_num,
            "prompt": full_prompt,
            "seed": page_seed,
            "variation": variation,
        })

    # Handle resume mode
    manifest_path = output_dir / "manifest.jsonl"
    completed = load_manifest(manifest_path) if resume else {}

    pages_to_generate = [
        p for p in page_configs
        if p["page_num"] not in completed or completed[p["page_num"]].get("status") != "success"
    ]

    console.print(f"\n[bold]Coloring Book Generator[/bold]")
    console.print(f"Subject: {prompt}")
    console.print(f"Total pages: {pages}")
    console.print(f"Pages to generate: {len(pages_to_generate)}")
    console.print(f"Output directory: {output_dir}")
    console.print(f"Model ID: {model_id or '(default)'}")
    console.print(f"Dimensions: {width}x{height}px")
    console.print(f"Concurrency: {concurrency}")
    console.print()

    if dry_run:
        console.print("[yellow]Dry run - showing planned generations:[/yellow]\n")
        for config in pages_to_generate[:10]:
            console.print(f"Page {config['page_num']}: seed={config['seed']}")
            console.print(f"  Prompt: {config['prompt'][:80]}...")
        if len(pages_to_generate) > 10:
            console.print(f"  ... and {len(pages_to_generate) - 10} more")
        return

    if not pages_to_generate:
        console.print("[green]All pages already generated![/green]")
        return

    # Verify API key
    console.print("Verifying API key...")
    client = LeonardoClient(api_key)

    try:
        user = client.verify_api_key()
        console.print(f"[green]Authenticated as: {user.username or user.id}[/green]")
        if user.apiCredit is not None:
            console.print(f"API credits: {user.apiCredit}")
    except LeonardoAuthError as e:
        console.print(f"[red]Authentication failed:[/red] {e}")
        raise typer.Exit(1)

    # Generate pages
    success_count = 0
    fail_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Generating pages...", total=len(pages_to_generate))

        # Use thread pool for concurrent generation
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = {}
            for config in pages_to_generate:
                future = executor.submit(
                    generate_single_page,
                    client=client,
                    page_num=config["page_num"],
                    prompt=config["prompt"],
                    negative_prompt=negative_prompt,
                    output_dir=output_dir,
                    model_id=model_id,
                    seed=config["seed"],
                    width=width,
                    height=height,
                )
                futures[future] = config["page_num"]

            for future in as_completed(futures):
                page_num = futures[future]
                result = future.result()

                # Write result to manifest
                append_to_manifest(manifest_path, result)

                if result["status"] == "success":
                    success_count += 1
                    logger.info(f"Page {page_num}: Generated successfully")
                else:
                    fail_count += 1
                    logger.warning(f"Page {page_num}: Failed - {result.get('error')}")

                progress.update(task, advance=1)

    console.print()
    console.print(f"[bold]Generation complete![/bold]")
    console.print(f"  [green]Success:[/green] {success_count}")
    if fail_count:
        console.print(f"  [red]Failed:[/red] {fail_count}")
        console.print(f"\nRun with [bold]--resume[/bold] to retry failed pages")

    console.print(f"\nImages saved to: {output_dir}")
    console.print(f"Manifest: {manifest_path}")

    client.close()


@app.command()
def status(
    output_dir: Path = typer.Argument(
        None,
        help="Output directory to check",
    ),
) -> None:
    """Show status of a generation run."""
    if output_dir is None:
        base_output = Path(os.getenv("OUTPUT_DIR", "outputs"))
        book_slug = os.getenv("BOOK_SLUG", "coloring_book")
        output_dir = base_output / book_slug

    manifest_path = output_dir / "manifest.jsonl"
    if not manifest_path.exists():
        console.print(f"No manifest found at {manifest_path}")
        return

    completed = load_manifest(manifest_path)
    success = [e for e in completed.values() if e.get("status") == "success"]
    failed = [e for e in completed.values() if e.get("status") == "failed"]

    console.print(f"\n[bold]Generation Status[/bold]")
    console.print(f"Directory: {output_dir}")
    console.print(f"Total entries: {len(completed)}")
    console.print(f"  [green]Success:[/green] {len(success)}")
    console.print(f"  [red]Failed:[/red] {len(failed)}")

    if failed:
        console.print("\n[yellow]Failed pages:[/yellow]")
        for entry in failed[:5]:
            console.print(f"  Page {entry['page_num']}: {entry.get('error', 'Unknown error')}")
        if len(failed) > 5:
            console.print(f"  ... and {len(failed) - 5} more")


if __name__ == "__main__":
    app()
