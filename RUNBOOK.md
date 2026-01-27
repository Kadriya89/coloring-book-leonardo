# Coloring Book Generator - Operational Runbook

Step-by-step guide to generate a complete coloring book using Leonardo AI.

## Prerequisites

Before you begin, ensure you have:

1. **Python 3.10 or higher** installed
2. **Leonardo AI API key** from [app.leonardo.ai](https://app.leonardo.ai)
3. **Terminal/Command Prompt** access

## Initial Setup (One-Time)

### Step 1: Install Dependencies

Open a terminal and navigate to the project directory:

```bash
cd coloring_book_leonardo

# Create virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### Step 2: Configure API Key

```bash
# Copy the example config
cp .env.example .env

# Edit .env and add your API key
# LEONARDO_API_KEY=your_key_here
```

### Step 3: Verify API Connection

```bash
python scripts/list_models.py
```

You should see a list of available models. If you get an authentication error, check your API key.

### Step 4: Select a Model (Optional)

Choose a model from the list and add its ID to `.env`:

```env
MODEL_ID=your_chosen_model_id
```

If you skip this, the system uses Leonardo's default model.

---

## Generating a Coloring Book

### Step 1: Plan Your Book

Decide on:
- **Theme**: What's your book about? (mandalas, animals, nature, etc.)
- **Page count**: How many pages? (default: 50)
- **Variations**: Should pages have variety within the theme?

### Step 2: Generate Prompt Variations (Recommended)

Create varied prompts for visual diversity:

```bash
# View available themes
python scripts/make_variations.py themes

# Generate variations for your theme
python scripts/make_variations.py "mandala design" \
  --theme mandala \
  --count 10 \
  --output prompts/variations.yaml
```

This creates 10 variations, each getting 5 different seeds = 50 unique pages.

### Step 3: Start Generation

```bash
python scripts/generate_pages.py \
  --prompt "mandala design" \
  --pages 50 \
  --output-dir outputs/mandala_book
```

**What happens:**
1. Script verifies your API key
2. Creates output directory
3. Generates pages (with progress bar)
4. Downloads each image
5. Saves progress to manifest.jsonl

**This takes time!** Each page requires:
- API request submission
- Generation time (30-60 seconds)
- Download

### Step 4: Monitor Progress

The script shows a progress bar. If you need to stop:
- Press Ctrl+C to interrupt
- Run with `--resume` to continue later

### Step 5: Resume If Interrupted

```bash
python scripts/generate_pages.py \
  --prompt "mandala design" \
  --pages 50 \
  --output-dir outputs/mandala_book \
  --resume
```

The script skips completed pages automatically.

---

## Quality Assurance

### Step 1: Validate Images

```bash
python scripts/validate_images.py outputs/mandala_book
```

This checks:
- Correct dimensions (2550×3300)
- White background presence
- Black line content
- No color (grayscale)
- File integrity

### Step 2: Review Failed Images

The validation report shows which images failed and why. Common issues:

| Issue | Solution |
|-------|----------|
| Wrong dimensions | Re-generate with correct settings |
| Contains color | Post-process with `--binarize` |
| Too little content | Adjust prompt, try again |
| Corrupted file | Re-download or re-generate |

### Step 3: Manually Review (Recommended)

Open the output directory and visually inspect images. Look for:
- Appropriate complexity for coloring
- Complete designs (not cut off)
- No unwanted artifacts

---

## Post-Processing (Optional but Recommended)

### Clean Up for Print

```bash
python scripts/postprocess_lineart.py outputs/mandala_book \
  --binarize \
  --threshold 128 \
  --remove-aa \
  --margin 2.0 \
  --output outputs/mandala_book_processed
```

**Options explained:**
- `--binarize`: Convert to pure black and white
- `--threshold 128`: Gray values above this become white
- `--remove-aa`: Remove anti-aliasing blur
- `--margin 2.0`: Add 2% white margin for printing

### Preview Before Full Processing

```bash
python scripts/postprocess_lineart.py preview outputs/mandala_book/page_001.png \
  --binarize \
  --threshold 128
```

---

## Creating the PDF

### Basic PDF

```bash
python scripts/assemble_pdf.py outputs/mandala_book_processed \
  --output "My_Coloring_Book.pdf"
```

### Professional PDF with Title Page

```bash
python scripts/assemble_pdf.py outputs/mandala_book_processed \
  --output "My_Coloring_Book.pdf" \
  --title "Mandala Magic" \
  --subtitle "A Coloring Journey" \
  --page-numbers \
  --toc \
  --page-size letter \
  --margin 0.5
```

### PDF Options

| Option | Description |
|--------|-------------|
| `--title` | Add title page |
| `--subtitle` | Subtitle on title page |
| `--page-numbers` | Number each page |
| `--toc` | Table of contents |
| `--page-size` | letter, a4, square8, square10 |
| `--margin` | Margin in inches |
| `--bleed` | Bleed area for pro printing |

---

## Complete Workflow Example

Here's a complete run from start to finish:

```bash
# 1. Setup (first time only)
cd coloring_book_leonardo
source venv/bin/activate

# 2. Verify API
python scripts/list_models.py

# 3. Create variations
python scripts/make_variations.py "zen garden with koi fish" \
  --theme nature \
  --output prompts/variations.yaml

# 4. Generate 50 pages
python scripts/generate_pages.py \
  --prompt "zen garden with koi fish" \
  --pages 50 \
  --output-dir outputs/zen_garden

# 5. Validate
python scripts/validate_images.py outputs/zen_garden

# 6. Post-process
python scripts/postprocess_lineart.py outputs/zen_garden \
  --binarize \
  --output outputs/zen_garden_final

# 7. Create PDF
python scripts/assemble_pdf.py outputs/zen_garden_final \
  --output "Zen_Garden_Coloring_Book.pdf" \
  --title "Zen Garden" \
  --page-numbers

# 8. Done! Open the PDF
open "Zen_Garden_Coloring_Book.pdf"  # macOS
# or: start "Zen_Garden_Coloring_Book.pdf"  # Windows
```

---

## Troubleshooting

### "API key invalid"

1. Check `.env` file exists and has `LEONARDO_API_KEY=`
2. Verify key is correct (no extra spaces)
3. Check key is still valid on Leonardo AI dashboard

### "Rate limit exceeded"

```bash
# Reduce concurrency
python scripts/generate_pages.py --prompt "..." --concurrency 1
```

### Generation stuck/slow

- Each image takes 30-60 seconds
- Check API status on Leonardo dashboard
- Try generating fewer pages first

### Images have color/shading

Post-process with binarization:
```bash
python scripts/postprocess_lineart.py outputs/book --binarize
```

### Need to use a different seed

```bash
python scripts/generate_pages.py --prompt "..." --seed 12345
```

### PDF too large

- Use JPEG format in post-processing
- Reduce quality setting

---

## Tips for Best Results

1. **Test first**: Generate 2-3 pages before committing to 50
2. **Vary prompts**: Use `make_variations.py` for diverse pages
3. **Use seeds**: Set a base seed for reproducibility
4. **Post-process**: Always run binarization for cleanest output
5. **Review manually**: AI isn't perfect, spot-check results
6. **Save manifests**: Keep `manifest.jsonl` for future reference

---

## Estimated Time

| Pages | Generation Time | Post-Processing | PDF Assembly |
|-------|-----------------|-----------------|--------------|
| 10 | ~10-15 min | ~1 min | ~30 sec |
| 25 | ~25-40 min | ~2 min | ~1 min |
| 50 | ~50-80 min | ~3 min | ~2 min |

*Times vary based on API response time and concurrency settings.*

---

## Getting Help

- Check error messages carefully - they usually explain the issue
- Run with `LOG_LEVEL=DEBUG` in `.env` for verbose output
- See `scripts/manual_mode.md` for manual web interface fallback
- Review README.md for additional documentation
