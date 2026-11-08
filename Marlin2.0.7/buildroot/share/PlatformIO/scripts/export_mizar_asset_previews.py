#!/usr/bin/env python3
"""Export MKS/LVGL RGB565 .bin icons as viewable PNG previews.

LVGL v7 true-color binary images start with a 4-byte image header followed by
little-endian RGB565 pixels. This recovers the quantized image, not the original
JPEG/PNG source. FontUNIGBK.bin is not an image and is deliberately ignored.
"""
from pathlib import Path
import struct
import sys

from PIL import Image, ImageDraw


def decode_rgb565(path: Path) -> Image.Image:
    data = path.read_bytes()
    if len(data) < 4:
        raise ValueError("file is shorter than the LVGL image header")

    # LVGL v7 packs cf:5, always_zero:3, width:11 and height:11 into 4 bytes.
    b0, b1, b2, b3 = data[:4]
    color_format = b0 & 0x1F
    width = b1 | ((b2 & 0x07) << 8)
    height = ((b2 >> 3) & 0x1F) | (b3 << 5)
    if color_format != 4:
        raise ValueError(f"unsupported LVGL color format {color_format}; expected RGB565 (4)")
    if not width or not height:
        raise ValueError(f"invalid image dimensions {width}x{height}")

    expected_size = 4 + width * height * 2
    if len(data) != expected_size:
        raise ValueError(
            f"size mismatch for {width}x{height}: got {len(data)} bytes, "
            f"expected {expected_size}"
        )

    pixels = []
    for (value,) in struct.iter_unpack("<H", data[4:]):
        red5 = (value >> 11) & 0x1F
        green6 = (value >> 5) & 0x3F
        blue5 = value & 0x1F
        pixels.append(((red5 * 255 + 15) // 31,
                       (green6 * 255 + 31) // 63,
                       (blue5 * 255 + 15) // 31))

    image = Image.new("RGB", (width, height))
    image.putdata(pixels)
    return image


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: export_mizar_asset_previews.py ASSETS_DIR OUTPUT_DIR")

    assets_dir, output_dir = map(Path, sys.argv[1:])
    if not assets_dir.is_dir():
        raise SystemExit(f"Assets directory not found: {assets_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    bins = sorted(p for p in assets_dir.glob("*.bin")
                  if p.name.lower() != "fontunigbk.bin")
    if not bins:
        raise SystemExit(f"No image .bin files found in {assets_dir}")

    decoded = []
    failures = []
    for path in bins:
        try:
            image = decode_rgb565(path)
            target = output_dir / f"{path.stem}.png"
            image.save(target, format="PNG", optimize=True)
            decoded.append((path.name, image))
            print(f"Decoded {path.name}: {image.width}x{image.height} -> {target}")
        except (OSError, ValueError) as error:
            failures.append(f"{path.name}: {error}")

    if failures:
        raise SystemExit("Could not decode every image asset:\n" + "\n".join(failures))

    # A labeled overview makes it practical to review all UI icons from the artifact.
    cell_w, cell_h, label_h, columns = 160, 120, 30, 5
    rows = (len(decoded) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_w, rows * (cell_h + label_h)), "#30343b")
    draw = ImageDraw.Draw(sheet)
    for index, (name, image) in enumerate(decoded):
        x = (index % columns) * cell_w
        y = (index // columns) * (cell_h + label_h)
        preview = image.copy()
        preview.thumbnail((cell_w - 12, cell_h - 12), Image.Resampling.NEAREST)
        px = x + (cell_w - preview.width) // 2
        py = y + (cell_h - preview.height) // 2
        sheet.paste(preview, (px, py))
        draw.text((x + 5, y + cell_h + 5), name[:24], fill="white")
    sheet.save(output_dir / "contact-sheet.png", format="PNG", optimize=True)
    print(f"Exported {len(decoded)} PNG previews and contact-sheet.png to {output_dir}")


if __name__ == "__main__":
    main()
