from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from PIL import Image


def square_rgba(source: Path, target_size: int = 1024) -> Image.Image:
    img = Image.open(source).convert("RGBA")
    side = max(img.width, img.height)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.alpha_composite(img, ((side - img.width) // 2, (side - img.height) // 2))
    if side != target_size:
        canvas = canvas.resize((target_size, target_size), Image.LANCZOS)
    return canvas


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
        base.resize((size, size), Image.LANCZOS).save(iconset_dir / filename, format="PNG")

    subprocess.run(
        [iconutil, "-c", "icns", str(iconset_dir), "-o", str(out_icns)],
        check=True,
    )
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate app icon files for packaging.")
    parser.add_argument("--source", default="assets/app_icon.png", help="Source PNG logo path")
    parser.add_argument("--ico", default="assets/app_icon.ico", help="Output ICO path")
    parser.add_argument("--icns", default="assets/app_icon.icns", help="Output ICNS path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    src = Path(args.source)
    if not src.exists():
        raise FileNotFoundError(f"Source icon not found: {src}")

    base = square_rgba(src, target_size=1024)
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
