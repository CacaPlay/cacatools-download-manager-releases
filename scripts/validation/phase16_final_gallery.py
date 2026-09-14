#!/usr/bin/env python3
"""Build a deterministic contact sheet from the final Phase 16 UI captures.

The individual screenshots remain the source of truth. This gallery is only a
compact visual index for the final handoff, so users can compare layouts,
themes, media analysis and recovery without opening every PNG separately.
"""
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[2]
SCREENSHOTS = ROOT / "docs" / "screenshots" / "phase16"
OUTPUT = SCREENSHOTS / "final-gallery.png"

CASES = (
    ("command-center-dark-1920x1080.png", "Command Center · oscuro"),
    ("zen-sidebar-dark-1920x1080.png", "Zen Sidebar · oscuro"),
    ("command-center-light-1920x1080.png", "Command Center · claro"),
    ("zen-sidebar-light-1920x1080.png", "Zen Sidebar · claro"),
    ("dialog-video-1440x900.png", "Análisis de vídeo y calidad"),
    ("dialog-page-alternatives-1280x800.png", "Recuperación y alternativas"),
)

CANVAS_WIDTH = 1800
MARGIN = 48
GAP = 28
HEADER_HEIGHT = 132
COLUMNS = 2
TILE_WIDTH = (CANVAS_WIDTH - MARGIN * 2 - GAP) // COLUMNS
IMAGE_HEIGHT = 455
CAPTION_HEIGHT = 64
TILE_HEIGHT = IMAGE_HEIGHT + CAPTION_HEIGHT
ROWS = (len(CASES) + COLUMNS - 1) // COLUMNS
CANVAS_HEIGHT = HEADER_HEIGHT + MARGIN + ROWS * TILE_HEIGHT + (ROWS - 1) * GAP + MARGIN


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def fit_image(source: Image.Image) -> Image.Image:
    image = source.convert("RGB")
    return ImageOps.fit(image, (TILE_WIDTH, IMAGE_HEIGHT), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def rounded_panel(canvas: Image.Image, box: tuple[int, int, int, int], radius: int = 22) -> None:
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(box, radius=radius, fill=(15, 20, 27), outline=(46, 58, 72), width=2)


def main() -> int:
    missing = [str(SCREENSHOTS / name) for name, _ in CASES if not (SCREENSHOTS / name).is_file()]
    if missing:
        raise SystemExit("Faltan capturas para la galería final:\n" + "\n".join(missing))

    canvas = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), (6, 10, 15))
    draw = ImageDraw.Draw(canvas)
    title_font = font(42, bold=True)
    subtitle_font = font(22)
    caption_font = font(23, bold=True)

    draw.text((MARGIN, 34), "CacaTools Download Manager · Fase 16", font=title_font, fill=(242, 246, 250))
    draw.text(
        (MARGIN, 88),
        "Capturas reproducibles del frontend final: layouts, modos visuales, análisis y recuperación.",
        font=subtitle_font,
        fill=(148, 160, 176),
    )

    for index, (filename, caption) in enumerate(CASES):
        row, column = divmod(index, COLUMNS)
        x = MARGIN + column * (TILE_WIDTH + GAP)
        y = HEADER_HEIGHT + MARGIN + row * (TILE_HEIGHT + GAP)
        rounded_panel(canvas, (x, y, x + TILE_WIDTH, y + TILE_HEIGHT))
        with Image.open(SCREENSHOTS / filename) as source:
            fitted = fit_image(source)
        mask = Image.new("L", fitted.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, TILE_WIDTH, IMAGE_HEIGHT + 18), radius=20, fill=255)
        canvas.paste(fitted, (x, y), mask)
        draw.text((x + 22, y + IMAGE_HEIGHT + 17), caption, font=caption_font, fill=(231, 236, 242))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUTPUT, format="PNG", optimize=True)
    print(f"OK: galería final creada en {OUTPUT.relative_to(ROOT)} ({CANVAS_WIDTH}x{CANVAS_HEIGHT}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
