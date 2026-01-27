# Manual Mode Instructions

If the automated scripts fail or you prefer manual control, follow these steps to generate coloring book pages using Leonardo AI directly.

## Prerequisites

1. Leonardo AI account with API access
2. API key from [Leonardo AI Dashboard](https://app.leonardo.ai/api)

## Step 1: Access Leonardo AI

1. Go to [Leonardo AI](https://app.leonardo.ai)
2. Log in to your account
3. Navigate to "AI Image Generation"

## Step 2: Configure Generation Settings

### Recommended Settings for Coloring Book Pages

| Setting | Value | Notes |
|---------|-------|-------|
| **Dimensions** | 2550 × 3300 px | 8.5×11" at 300 DPI |
| **Model** | Leonardo Diffusion XL | Or similar high-quality model |
| **Guidance Scale** | 7-9 | Higher = more prompt adherence |
| **Alchemy** | Off | Keep simple for line art |

### Alternative Dimensions

- **Letter (8.5×11")**: 2550 × 3300 px
- **A4 (210×297mm)**: 2480 × 3508 px
- **Square (8×8")**: 2400 × 2400 px

## Step 3: Craft Your Prompt

### Base Prompt Template

```
[SUBJECT], black and white line art, coloring book page style,
clean outlines, no shading, no gradients, no fills,
intricate details suitable for adult coloring,
white background, crisp black lines
```

### Example Prompts

**Mandala:**
```
intricate mandala with floral elements, black and white line art,
coloring book page style, clean outlines, no shading, no gradients,
symmetrical design, white background, crisp black lines
```

**Animals:**
```
majestic lion portrait with decorative patterns, black and white line art,
coloring book page style, clean outlines, no shading, zentangle inspired,
white background, intricate details for adult coloring
```

**Nature:**
```
enchanted forest scene with mushrooms and ferns, black and white line art,
coloring book page style, clean outlines, no shading, no fills,
whimsical illustration, white background, detailed botanical elements
```

## Step 4: Negative Prompt

Always use this negative prompt to ensure clean line art:

```
color, colored, shading, gradient, blur, blurry,
gray, grayscale fills, shadows, realistic, photograph,
3D render, painting style, texture, noise
```

## Step 5: Generate and Download

1. Click "Generate" to create images
2. Review the results
3. Download images you want to use (PNG format recommended)
4. Save with sequential naming: `page_001.png`, `page_002.png`, etc.

## Step 6: Organize Your Files

Create this folder structure:

```
my_coloring_book/
├── raw/           # Original downloads
├── processed/     # After post-processing
└── final/         # Print-ready files
```

## Step 7: Validate Images

Check each image for:

- [ ] Correct dimensions (2550×3300 px for letter size)
- [ ] Pure black and white (no gray or color)
- [ ] Clean white background
- [ ] Sufficient line detail
- [ ] No artifacts or noise

## Step 8: Post-Processing (Optional)

If images need cleanup:

1. Open in image editor (Photoshop, GIMP, etc.)
2. Convert to grayscale: Image → Mode → Grayscale
3. Adjust levels to increase contrast
4. Apply threshold to remove gray: Image → Adjustments → Threshold
5. Save as PNG

## Step 9: Assemble PDF

Use any PDF tool to combine images:

**Using Preview (macOS):**
1. Select all images in Finder
2. Right-click → Open With → Preview
3. File → Print → Save as PDF

**Using online tools:**
- [iLovePDF](https://www.ilovepdf.com/jpg_to_pdf)
- [Smallpdf](https://smallpdf.com/jpg-to-pdf)

**Using command line (ImageMagick):**
```bash
convert page_*.png -page Letter coloring_book.pdf
```

## Troubleshooting

### Images have color or shading
- Strengthen negative prompt
- Try different model
- Reduce guidance scale slightly

### Lines too thin or faint
- Add "bold lines" or "thick outlines" to prompt
- Post-process with threshold adjustment

### Wrong dimensions
- Check model supports custom dimensions
- Some models have maximum size limits

### Generation fails
- Check API credits/quota
- Try smaller dimensions first
- Simplify prompt

## API Rate Limits

Leonardo AI has these typical limits:
- ~150 images per day (free tier)
- Higher limits with paid plans
- Wait 30 seconds between requests to avoid rate limiting

## Quick Reference Card

```
DIMENSIONS: 2550 × 3300 px
MODEL: Leonardo Diffusion XL (or similar)

PROMPT FORMULA:
[subject] + [style modifiers] + [technical requirements]

STYLE MODIFIERS:
- black and white line art
- coloring book page style
- clean outlines
- no shading, no gradients, no fills
- white background
- crisp black lines

NEGATIVE PROMPT:
color, shading, gradient, blur, gray, shadows,
realistic, 3D render, painting style
```

## Need Help?

- [Leonardo AI Documentation](https://docs.leonardo.ai)
- [Leonardo AI Discord](https://discord.gg/leonardo-ai)
- Check the main README.md for script-based automation
