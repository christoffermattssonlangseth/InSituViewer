#!/usr/bin/env python3
"""Generate macOS-style app icon assets for InSituCore."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
BASE_PNG = ASSETS / "app_icon_1024.png"
ICNS_PATH = ASSETS / "InSituCore.icns"
ICONSET_DIR = ASSETS / "InSituCore.iconset"


def _lerp(a: int, b: int, t: float) -> int:
    return int(round(a + (b - a) * t))


def _build_background(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()

    top = (53, 71, 87)
    bottom = (29, 40, 53)
    left_tint = (44, 86, 97, 46)
    right_tint = (83, 100, 119, 38)

    for y in range(size):
        t = y / (size - 1)
        for x in range(size):
            r = _lerp(top[0], bottom[0], t)
            g = _lerp(top[1], bottom[1], t)
            b = _lerp(top[2], bottom[2], t)
            lt = int(left_tint[3] * (1 - x / (size - 1)))
            rt = int(right_tint[3] * (x / (size - 1)))
            r = min(255, r + (left_tint[0] * lt + right_tint[0] * rt) // 255)
            g = min(255, g + (left_tint[1] * lt + right_tint[1] * rt) // 255)
            b = min(255, b + (left_tint[2] * lt + right_tint[2] * rt) // 255)
            px[x, y] = (r, g, b, 255)
    return img


def _rounded_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return mask


def make_base_icon(size: int = 1024) -> Image.Image:
    icon = _build_background(size)
    mask = _rounded_mask(size, int(size * 0.225))
    cut = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    cut.paste(icon, (0, 0), mask)
    icon = cut

    draw = ImageDraw.Draw(icon)

    # Soft top sheen for a native macOS icon finish.
    sheen = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sheen)
    sd.ellipse(
        (-int(size * 0.08), -int(size * 0.44), int(size * 1.08), int(size * 0.54)),
        fill=(255, 255, 255, 28),
    )
    sheen = sheen.filter(ImageFilter.GaussianBlur(radius=size * 0.025))
    icon.alpha_composite(sheen)

    cx, cy = size // 2, size // 2
    ring_radius = int(size * 0.235)
    ring_width = int(size * 0.06)

    # Main ring.
    draw.ellipse(
        (cx - ring_radius, cy - ring_radius, cx + ring_radius, cy + ring_radius),
        outline=(236, 243, 247, 230),
        width=ring_width,
    )

    # Inner core.
    core_r = int(size * 0.105)
    draw.ellipse(
        (cx - core_r, cy - core_r, cx + core_r, cy + core_r),
        fill=(223, 236, 242, 232),
    )

    # Satellite nodes hinting at spatial compartments.
    nodes = [
        (cx - int(size * 0.19), cy - int(size * 0.12), int(size * 0.040), (162, 208, 214, 245)),
        (cx + int(size * 0.21), cy - int(size * 0.01), int(size * 0.036), (188, 210, 233, 245)),
        (cx - int(size * 0.02), cy + int(size * 0.22), int(size * 0.044), (140, 192, 201, 245)),
    ]
    for nx, ny, nr, color in nodes:
        draw.line((cx, cy, nx, ny), fill=(236, 243, 247, 105), width=max(3, int(size * 0.008)))
        draw.ellipse((nx - nr, ny - nr, nx + nr, ny + nr), fill=color)
        # subtle inner highlight
        h = int(nr * 0.35)
        draw.ellipse((nx - h, ny - h, nx + h, ny + h), fill=(246, 251, 253, 160))

    # Rim shadow for depth on light backgrounds.
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sh = ImageDraw.Draw(shadow)
    sh.rounded_rectangle(
        (int(size * 0.015), int(size * 0.015), int(size * 0.985), int(size * 0.985)),
        radius=int(size * 0.225),
        outline=(0, 0, 0, 62),
        width=max(2, int(size * 0.01)),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=size * 0.012))
    icon.alpha_composite(shadow)

    return icon


def write_iconset(base_img: Image.Image) -> None:
    if ICONSET_DIR.exists():
        shutil.rmtree(ICONSET_DIR)
    ICONSET_DIR.mkdir(parents=True, exist_ok=True)

    icon_sizes = [16, 32, 128, 256, 512]
    for size in icon_sizes:
        base_img.resize((size, size), Image.Resampling.LANCZOS).save(
            ICONSET_DIR / f"icon_{size}x{size}.png"
        )
        double = size * 2
        base_img.resize((double, double), Image.Resampling.LANCZOS).save(
            ICONSET_DIR / f"icon_{size}x{size}@2x.png"
        )


def build_icns() -> None:
    # First try native iconutil. Some environments have stricter iconset validation,
    # so we fall back to Pillow's ICNS writer for portability.
    if shutil.which("iconutil") is not None:
        if ICNS_PATH.exists():
            ICNS_PATH.unlink()
        try:
            subprocess.run(
                ["iconutil", "--convert", "icns", str(ICONSET_DIR), "--output", str(ICNS_PATH)],
                check=True,
            )
            return
        except subprocess.CalledProcessError:
            pass

    base = Image.open(BASE_PNG).convert("RGBA")
    if ICNS_PATH.exists():
        ICNS_PATH.unlink()
    base.save(
        ICNS_PATH,
        format="ICNS",
        sizes=[(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512), (1024, 1024)],
    )


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    base = make_base_icon(1024)
    base.save(BASE_PNG)
    write_iconset(base)
    build_icns()
    print(f"Wrote {BASE_PNG}")
    print(f"Wrote {ICONSET_DIR}")
    if ICNS_PATH.exists():
        print(f"Wrote {ICNS_PATH}")


if __name__ == "__main__":
    main()
