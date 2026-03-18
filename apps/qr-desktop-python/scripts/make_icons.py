from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageFilter


def _alpha_bbox(img: Image.Image) -> tuple[int, int, int, int] | None:
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    alpha = img.getchannel("A")
    return alpha.getbbox()


def square_rgba(source: Path, target_size: int = 1024, padding_ratio: float = 0.1) -> Image.Image:
    img = Image.open(source).convert("RGBA")

    bbox = _alpha_bbox(img)
    if bbox is not None:
        img = img.crop(bbox)

    work_size = max(1, int(target_size * max(0.0, min(0.4, padding_ratio))))
    icon_area = target_size - (2 * work_size)

    scale = min(icon_area / max(1, img.width), icon_area / max(1, img.height))
    resized = img.resize(
        (max(1, int(img.width * scale)), max(1, int(img.height * scale))),
        Image.LANCZOS,
    )

    canvas = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))
    canvas.alpha_composite(
        resized,
        ((target_size - resized.width) // 2, (target_size - resized.height) // 2),
    )
    return canvas


def _icon_resize(base: Image.Image, size: int) -> Image.Image:
    out = base.resize((size, size), Image.LANCZOS)
    if size <= 64:
        out = out.filter(ImageFilter.UnsharpMask(radius=1.0, percent=170, threshold=1))
    return out


def build_ico(base: Image.Image, out_ico: Path) -> None:
    out_ico.parent.mkdir(parents=True, exist_ok=True)
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    base.save(out_ico, format="ICO", sizes=sizes)


def build_icns(base: Image.Image, out_icns: Path) -> bool:
    iconutil = shutil.which("iconutil")
    if not iconutil:
        return False

    iconset_dir = out_icns.with_suffix(".iconset")
    iconset_dir.mkdir(parents=True, exist_ok=True)

    mapping = {
        "icon_16x16.png": 16,
        "icon_16x16@2x.png": 32,
        "icon_32x32.png": 32,
        "icon_32x32@2x.png": 64,
        "icon_128x128.png": 128,
        "icon_128x128@2x.png": 256,
        "icon_256x256.png": 256,
        "icon_256x256@2x.png": 512,
        "icon_512x512.png": 512,
        "icon_512x512@2x.png": 1024,
    }
    for filename, size in mapping.items():
        _icon_resize(base, size).save(iconset_dir / filename, format="PNG")

    subprocess.run(
        [iconutil, "-c", "icns", str(iconset_dir), "-o", str(out_icns)],
        check=True,
    )
    return True


def parse_args() -> argparse.Namespace:
    default_source = "../../shared/assets/app_icon.png"
    default_ico = "../../shared/assets/app_icon.ico"
    default_icns = "../../shared/assets/app_icon.icns"

    parser = argparse.ArgumentParser(description="Generate app icon files for packaging.")
    parser.add_argument("--source", default=default_source, help="Source PNG logo path")
    parser.add_argument("--ico", default=default_ico, help="Output ICO path")
    parser.add_argument("--icns", default=default_icns, help="Output ICNS path")
    parser.add_argument(
        "--padding-ratio",
        type=float,
        default=0.10,
        help="Inner padding ratio for the icon content (0.0 to 0.4).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    src = Path(args.source)
    if not src.exists():
        raise FileNotFoundError(f"Source icon not found: {src}")

    base = square_rgba(src, target_size=1024, padding_ratio=args.padding_ratio)
    build_ico(base, Path(args.ico))
    icns_ok = build_icns(base, Path(args.icns))

    print(f"ICO generated: {args.ico}")
    if icns_ok:
        print(f"ICNS generated: {args.icns}")
    else:
        print("ICNS skipped: 'iconutil' not found (run this on macOS).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
