# Leonardo AI Coloring Book Generator

Generate 50+ print-ready coloring book pages using Leonardo AI's REST API. Produces high-quality black-and-white line art suitable for adult coloring books.

## Quick Start

```bash
# 1. Clone and setup
cd coloring_book_leonardo
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure API key
cp .env.example .env
# Edit .env and add your LEONARDO_API_KEY

# 3. Find available models
python scripts/list_models.py

# 4. Set MODEL_ID in .env (optional but recommended)

# 5. Generate pages
python scripts/generate_pages.py --prompt "mandala with floral elements" --pages 50

# 6. Validate and assemble
python scripts/validate_images.py outputs/coloring_book
python scripts/assemble_pdf.py outputs/coloring_book --output my_book.pdf
```

## Features

- **Automated Generation**: Generate 50+ pages with a single command
- **Smart Variations**: Automatic prompt variations for visual diversity
- **Resume Support**: Continue interrupted runs without re-generating
- **Image Validation**: Verify dimensions, colors, and quality
- **Post-Processing**: Binarization and cleanup for print-ready output
- **PDF Assembly**: Combine pages into a print-ready book

## Directory Structure

```
coloring_book_leonardo/
├── leonardo/                # API client library
│   ├── client.py           # Core API wrapper
│   ├── models.py           # Data models
│   └── exceptions.py       # Error handling
├── scripts/                 # CLI tools
│   ├── generate_pages.py   # Main generation script
│   ├── list_models.py      # List available models
│   ├── validate_images.py  # Image validation
│   ├── postprocess_lineart.py  # Image cleanup
│   ├── assemble_pdf.py     # PDF creation
│   └── make_variations.py  # Prompt variation generator
├── prompts/                 # Prompt templates
│   ├── base_prompts.yaml
│   └── negative_prompts.yaml
├── outputs/                 # Generated images
└── tests/                   # Test suite
```

## Configuration

Copy `.env.example` to `.env` and configure:

```env
# Required
LEONARDO_API_KEY=your_api_key_here

# Optional
MODEL_ID=             # Specific model to use
PAGE_COUNT=50         # Default number of pages
WIDTH_PX=2550         # 8.5" at 300 DPI
HEIGHT_PX=3300        # 11" at 300 DPI
CONCURRENCY=3         # Parallel requests
```

## Scripts

### generate_pages.py

Main generation script.

```bash
# Basic usage
python scripts/generate_pages.py --prompt "mandala design" --pages 50

# With options
python scripts/generate_pages.py \
  --prompt "butterfly garden" \
  --pages 25 \
  --output-dir outputs/butterflies \
  --seed 12345 \
  --resume  # Continue previous run
```

### list_models.py

View available Leonardo models.

```bash
python scripts/list_models.py
python scripts/list_models.py --featured  # Featured models only
python scripts/list_models.py --search "diffusion"
```

### validate_images.py

Check generated images for quality.

```bash
python scripts/validate_images.py outputs/coloring_book
python scripts/validate_images.py outputs/coloring_book --strict  # Exit on failures
```

### postprocess_lineart.py

Clean up images for printing.

```bash
# Convert to pure black and white
python scripts/postprocess_lineart.py outputs/coloring_book --binarize

# Full cleanup
python scripts/postprocess_lineart.py outputs/coloring_book \
  --binarize \
  --remove-aa \
  --margin 2.0 \
  --sharpen
```

### assemble_pdf.py

Create PDF from images.

```bash
python scripts/assemble_pdf.py outputs/coloring_book --output my_book.pdf

# With title page and page numbers
python scripts/assemble_pdf.py outputs/coloring_book \
  --output my_book.pdf \
  --title "My Coloring Book" \
  --page-numbers \
  --toc
```

### make_variations.py

Generate prompt variations for diversity.

```bash
python scripts/make_variations.py "mandala" --theme mandala --count 10
python scripts/make_variations.py themes  # List available themes
```

## Prompt Templates

Edit `prompts/base_prompts.yaml` to customize the generation style:

```yaml
base_template: |
  {subject}, black and white line art, coloring book page style,
  clean outlines, no shading, no gradients, no fills,
  intricate details suitable for adult coloring,
  white background, crisp black lines
```

## Print Specifications

Default settings produce print-ready output:

| Specification | Value |
|--------------|-------|
| Page Size | 8.5 × 11 inches (Letter) |
| Resolution | 300 DPI |
| Pixel Dimensions | 2550 × 3300 px |
| Color Mode | Black & White |
| Format | PNG |

## Troubleshooting

### API Authentication Errors

```bash
# Verify your API key
python scripts/list_models.py
```

### Rate Limiting

The default concurrency (3) respects rate limits. Reduce if you see 429 errors:

```bash
python scripts/generate_pages.py --prompt "..." --concurrency 1
```

### Resume Failed Generation

```bash
python scripts/generate_pages.py --prompt "..." --resume
```

### Image Quality Issues

Run post-processing for cleaner output:

```bash
python scripts/postprocess_lineart.py outputs/coloring_book --binarize --remove-aa
```

## Requirements

- Python 3.10+
- Leonardo AI API key
- Dependencies in `requirements.txt`

## License

MIT License - See LICENSE file for details.
