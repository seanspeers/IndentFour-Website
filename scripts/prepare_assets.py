#!/usr/bin/env python3
"""Create web-ready derivatives from the shipping Indent Four artwork."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
IMAGE_DIR = ROOT / "assets" / "images"
ICON_DIR = ROOT / "assets" / "icons"

APP_ICON = Path(
    "/Users/sean/RunPy/IndentFour/Resources/Assets.xcassets/"
    "AppIcon.appiconset/IndentFour-AppIcon.png"
)
IPHONE_DIR = Path(
    "/Users/sean/IndentFourResources/Screenshots/iPhone-6.9/Final"
)
IPAD_DIR = Path(
    "/Users/sean/IndentFourResources/Screenshots/iPad-13/Final"
)

SCREENSHOTS = {
    "hero-python": (IPHONE_DIR / "01-python-314.png", (660, 990)),
    "workspace-ipad": (IPAD_DIR / "01-python-workspace.png", (720, 1376)),
    "shortcuts": (IPHONE_DIR / "02-shortcuts.png", (660, 990)),
    "outputs-ipad": (IPAD_DIR / "03-real-files.png", (720, 1376)),
    "spreadsheet": (IPHONE_DIR / "04-spreadsheets.png", (660,)),
    "pdf": (IPHONE_DIR / "05-pdfs.png", (660,)),
    "device": (IPHONE_DIR / "07-device.png", (660,)),
    "examples": (IPHONE_DIR / "08-examples.png", (660,)),
}


def require_sources() -> None:
    missing = [APP_ICON]
    missing.extend(source for source, _ in SCREENSHOTS.values())
    missing = [path for path in missing if not path.is_file()]
    if missing:
        joined = "\n".join(f"- {path}" for path in missing)
        raise SystemExit(f"Missing source assets:\n{joined}")


def resize_to_width(image: Image.Image, width: int) -> Image.Image:
    if width > image.width:
        raise ValueError(f"Refusing to upscale {image.width}px image to {width}px")
    height = round(image.height * width / image.width)
    return image.resize((width, height), Image.Resampling.LANCZOS)


def save_picture_set(name: str, source: Path, widths: tuple[int, ...]) -> None:
    with Image.open(source) as original:
        image = ImageOps.exif_transpose(original).convert("RGB")
        for width in widths:
            resized = resize_to_width(image, width)
            stem = IMAGE_DIR / f"{name}-{width}"
            resized.save(stem.with_suffix(".avif"), "AVIF", quality=58, speed=6)
            resized.save(
                stem.with_suffix(".webp"),
                "WEBP",
                quality=86,
                method=6,
            )
            resized.save(
                stem.with_suffix(".png"),
                "PNG",
                optimize=True,
                compress_level=9,
            )


def save_icons() -> None:
    with Image.open(APP_ICON) as original:
        icon = ImageOps.exif_transpose(original).convert("RGB")
        for size, filename in (
            (16, "favicon-16.png"),
            (32, "favicon-32.png"),
            (48, "brand-48.png"),
            (180, "apple-touch-icon.png"),
            (192, "icon-192.png"),
            (512, "icon-512.png"),
        ):
            resized = icon.resize((size, size), Image.Resampling.LANCZOS)
            resized.save(ICON_DIR / filename, "PNG", optimize=True)

        icon.resize((512, 512), Image.Resampling.LANCZOS).save(
            IMAGE_DIR / "app-icon-512.avif", "AVIF", quality=62, speed=6
        )
        icon.resize((512, 512), Image.Resampling.LANCZOS).save(
            IMAGE_DIR / "app-icon-512.webp", "WEBP", quality=90, method=6
        )
        icon.resize((512, 512), Image.Resampling.LANCZOS).save(
            IMAGE_DIR / "app-icon-512.png", "PNG", optimize=True
        )

        icon.resize((32, 32), Image.Resampling.LANCZOS).save(
            ROOT / "favicon.ico", "ICO", sizes=[(16, 16), (32, 32)]
        )


def rounded_image(image: Image.Image, radius: int) -> Image.Image:
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, *image.size), radius=radius, fill=255)
    result = Image.new("RGB", image.size, "#0C172A")
    result.paste(image, mask=mask)
    return result


def save_social_image() -> None:
    canvas = Image.new("RGB", (1200, 630), "#0C172A")
    draw = ImageDraw.Draw(canvas)

    with Image.open(APP_ICON) as icon_source:
        icon = icon_source.convert("RGB").resize(
            (92, 92), Image.Resampling.LANCZOS
        )
        canvas.paste(rounded_image(icon, 19), (64, 62))

    with Image.open(IPAD_DIR / "01-python-workspace.png") as screenshot_source:
        screenshot = screenshot_source.convert("RGB").resize(
            (570, 428), Image.Resampling.LANCZOS
        )
        canvas.paste(rounded_image(screenshot, 18), (600, 101))

    regular = ImageFont.truetype("/System/Library/Fonts/SFNS.ttf", 29)
    semibold = ImageFont.truetype("/System/Library/Fonts/SFNS.ttf", 54)
    small = ImageFont.truetype("/System/Library/Fonts/SFNS.ttf", 22)
    draw.text((178, 88), "Indent Four", font=regular, fill="#FEFEFE")
    draw.multiline_text(
        (64, 214),
        "Python 3.14,\non your device.",
        font=semibold,
        fill="#FEFEFE",
        spacing=5,
    )
    draw.text(
        (64, 369),
        "Write scripts. Make useful files.",
        font=small,
        fill="#B9C5D8",
    )
    draw.rectangle((64, 512, 544, 514), fill="#197CFE")

    canvas.save(IMAGE_DIR / "social-card.png", "PNG", optimize=True)
    canvas.save(
        IMAGE_DIR / "social-card.webp", "WEBP", quality=90, method=6
    )


def main() -> None:
    require_sources()
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    for name, (source, widths) in SCREENSHOTS.items():
        save_picture_set(name, source, widths)
    save_icons()
    save_social_image()


if __name__ == "__main__":
    main()
