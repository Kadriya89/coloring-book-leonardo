# Claude Code Context - Coloring Book Generator

## IMPORTANT: User Profile

**The user of this project is NON-TECHNICAL.** They are not a programmer and should not be expected to:
- Write or modify code
- Run terminal commands themselves
- Understand technical error messages
- Know Python, git, or command-line tools

**Your role is to DO EVERYTHING FOR THEM.** Run all commands, handle all errors, and explain results in plain English.

---

## How to Help the User

### When the User Wants to Generate Coloring Book Pages

Simply ask them:
1. **What theme/subject?** (e.g., "mandalas", "flowers", "animals", "butterflies")
2. **How many pages?** (default: 50)

Then run everything for them:

```
# Claude Code should run these commands automatically:
source venv/bin/activate
WIDTH_PX=1024 HEIGHT_PX=1024 python scripts/generate_pages.py generate \
  --prompt "[USER'S THEME]" \
  --pages [NUMBER] \
  --output-dir outputs/[THEME_NAME]
```

**Note:** Use dimensions 1024x1024 or 1536x1536 as the default large dimensions (2550x3300) are not supported by the default model.

### When Generation is Complete

Automatically run validation and create the PDF:

```
# Post-process to black and white
python scripts/postprocess_lineart.py process outputs/[THEME] --binarize

# Create the PDF
python scripts/assemble_pdf.py assemble outputs/[THEME]/processed \
  --output "outputs/[THEME]/[Theme]_Coloring_Book.pdf" \
  --title "[User's Book Title]" \
  --page-numbers
```

Then tell the user: "Your coloring book is ready! The PDF is saved at: [path]"

### If Something Goes Wrong

- **Don't show technical errors to the user**
- Fix the problem yourself if possible
- If generation fails, use `--resume` to continue
- Explain in simple terms: "Some pages had issues, let me fix that..."

---

## Common User Requests & How to Handle Them

### "I want to make a coloring book"
→ Ask what theme they want, then run the full pipeline for them

### "Generate more pages" or "Add pages"
→ Run generate_pages.py with `--resume` flag

### "The images have color" or "Make them black and white"
→ Run postprocess_lineart.py with `--binarize`

### "Create a PDF" or "Put them in a book"
→ Run assemble_pdf.py with their preferred title

### "Show me what models are available"
→ Run `python scripts/list_models.py list-models` and summarize the results in plain English

### "Something went wrong" or errors occur
→ Check the manifest.jsonl, use `--resume`, and fix silently

---

## Quick Commands Reference (For Claude Code to Run)

### Setup (if not done)
```bash
cd /Users/kadriyabazarova/Projects/leonardo_1/coloring_book_leonardo
source venv/bin/activate
```

### Generate Pages
```bash
WIDTH_PX=1024 HEIGHT_PX=1024 python scripts/generate_pages.py generate \
  --prompt "THEME HERE" \
  --pages 50 \
  --output-dir outputs/FOLDER_NAME
```

### Resume Interrupted Generation
```bash
WIDTH_PX=1024 HEIGHT_PX=1024 python scripts/generate_pages.py generate \
  --prompt "THEME HERE" \
  --pages 50 \
  --output-dir outputs/FOLDER_NAME \
  --resume
```

### Post-Process to Black & White
```bash
python scripts/postprocess_lineart.py process outputs/FOLDER --binarize
```

### Create PDF
```bash
python scripts/assemble_pdf.py assemble outputs/FOLDER/processed \
  --output "My_Coloring_Book.pdf" \
  --title "My Coloring Book" \
  --page-numbers
```

### Validate Images
```bash
python scripts/validate_images.py validate outputs/FOLDER --width 1024 --height 1024
```

---

## Project Structure (For Claude Code Reference)

```
coloring_book_leonardo/
├── .env                    # API key (already configured)
├── venv/                   # Python environment (already set up)
├── scripts/
│   ├── generate_pages.py   # Main generation
│   ├── postprocess_lineart.py  # B&W conversion
│   ├── assemble_pdf.py     # PDF creation
│   ├── validate_images.py  # Quality checks
│   └── list_models.py      # Model listing
├── outputs/                # Where generated images go
└── prompts/                # Prompt templates
```

---

## Technical Notes (For Claude Code Only)

### API Limitations
- Default dimensions (2550x3300) are TOO LARGE for the default model
- Use 1024x1024 or 1536x1536 instead
- Generation takes ~30-60 seconds per image
- Concurrency default is 3 (can reduce if rate limited)

### Environment
- Virtual environment is at `./venv`
- Always activate with `source venv/bin/activate`
- API key is in `.env` file (already configured)

### Error Handling
- 400 "invalid dimensions" → Use smaller dimensions
- 429 Rate limit → Reduce concurrency or wait
- Generation timeout → Use `--resume` to continue
- Auth errors → Check API key in .env

### Dependencies
All installed in venv:
- httpx, pydantic, tenacity (API)
- Pillow (images)
- reportlab (PDF)
- typer, rich (CLI)
- eval_type_backport (Python 3.9 compatibility)

---

## Remember

1. **User is non-technical** - Don't show them commands or ask them to run things
2. **You run everything** - Execute all commands yourself
3. **Explain simply** - "Your book is ready!" not "Process exited with code 0"
4. **Handle errors gracefully** - Fix problems without alarming the user
5. **Generation takes time** - Let user know pages are being created (~1 min each)
