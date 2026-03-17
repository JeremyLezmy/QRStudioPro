from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import qrcode
from PIL import Image, ImageDraw, ImageFilter
from qrcode.constants import ERROR_CORRECT_H

try:
    import cv2
except ModuleNotFoundError:
    cv2 = None

from qr_presets import (
    GraphicConfig,
    apply_graphic_overrides,
    get_preset_graphic_config,
)

DEFAULT_OUTPUT_PATH = Path("generated_qrcode/qr_output.png")


@dataclass
class QRConfig:
    # Core content
    url: str = "https://phusis.io/"
    logo_path: Optional[Path] = None
    output_path: Path = field(default_factory=lambda: DEFAULT_OUTPUT_PATH)

    # QR technical settings
    error_correction: int = ERROR_CORRECT_H
    box_size: int = 22
    border: int = 4

    # Render behavior
    run_decode_check: bool = True
    verbose: bool = True

    # Graphic preset / style bundle
    graphic: GraphicConfig = field(default_factory=GraphicConfig)


def apply_preset(base: QRConfig, preset_name: Optional[str]) -> QRConfig:
    if preset_name:
        base.graphic = get_preset_graphic_config(preset_name)
    return base


def create_qr_config(
    url: str,
    preset_name: Optional[str],
    logo_path: Optional[Path] = None,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    graphic_overrides: Optional[Dict] = None,
    run_decode_check: bool = True,
    verbose: bool = True,
) -> QRConfig:
    cfg = QRConfig(
        url=url,
        logo_path=logo_path,
        output_path=output_path,
        run_decode_check=run_decode_check,
        verbose=verbose,
    )
    cfg = apply_preset(cfg, preset_name)
    if graphic_overrides:
        apply_graphic_overrides(cfg.graphic, graphic_overrides)
    return cfg


class BrandedQRGenerator:
    def __init__(self, config: QRConfig):
        self.cfg = config
        self.qr = qrcode.QRCode(
            version=None,
            error_correction=self.cfg.error_correction,
            box_size=self.cfg.box_size,
            border=self.cfg.border,
        )
        self.qr.add_data(self.cfg.url)
        self.qr.make(fit=True)

        self.base = self.qr.make_image(fill_color="black", back_color="white").convert("RGBA")
        self.w, self.h = self.base.size
        self.modules = self.qr.modules_count
        self.cell = self.w // (self.modules + 2 * self.cfg.border)
        self.offset = self.cfg.border * self.cell

    @property
    def g(self) -> GraphicConfig:
        return self.cfg.graphic

    # -------------------------
    # Utility
    # -------------------------

    @staticmethod
    def _np_color(c: Tuple[int, int, int]) -> np.ndarray:
        return np.array(c, dtype=np.uint8)

    def _diagonal_gradient(self, w: int, h: int, c1: Tuple[int, int, int], c2: Tuple[int, int, int]) -> np.ndarray:
        a = self._np_color(c1)
        b = self._np_color(c2)
        yy, xx = np.indices((h, w))
        t = ((xx + yy) / max(1, (w + h))).astype(np.float32)[..., None]
        return ((1 - t) * a + t * b).astype(np.uint8)

    def _mix_gradient(self, grad: np.ndarray, base_rgb: Optional[Tuple[int, int, int]], ratio: float) -> np.ndarray:
        if base_rgb is None:
            return grad
        base = self._np_color(base_rgb).astype(np.float32)
        g = grad.astype(np.float32)
        out = ratio * base + (1 - ratio) * g
        return np.clip(out, 0, 255).astype(np.uint8)

    def _debug(self, *args):
        if self.cfg.verbose:
            print(*args)

    # -------------------------
    # Logo
    # -------------------------

    def _load_logo(self, target_w: int) -> Image.Image:
        if self.cfg.logo_path is None:
            raise ValueError("Aucun logo configure (logo_path=None)")

        img = Image.open(self.cfg.logo_path).convert("RGBA")
        arr = np.array(img)

        if self.g.logo_remove_dark_bg:
            rgb = arr[:, :, :3].astype(np.int16)
            dark = np.max(rgb, axis=2) < self.g.logo_dark_bg_threshold
            arr[dark, 3] = 0

        alpha = arr[:, :, 3]
        ys, xs = np.where(alpha > 0)
        if len(xs):
            arr = arr[ys.min():ys.max() + 1, xs.min():xs.max() + 1]

        if self.g.recolor_logo:
            alpha_mask = arr[:, :, 3] > 0
            yy, xx = np.indices(arr.shape[:2])
            t = ((xx + yy) / max(1, arr.shape[0] + arr.shape[1])).astype(np.float32)[..., None]
            c1 = self._np_color(self.g.recolor_logo_start_rgb)
            c2 = self._np_color(self.g.recolor_logo_end_rgb)
            grad = ((1 - t) * c1 + t * c2).astype(np.uint8)
            arr[alpha_mask, :3] = grad[alpha_mask]

        logo = Image.fromarray(arr, "RGBA")
        scale = target_w / max(logo.size)
        return logo.resize(
            (max(1, int(logo.width * scale)), max(1, int(logo.height * scale))),
            Image.LANCZOS,
        )

    def _build_medallion(self, logo: Image.Image, dark_variant: bool = False) -> Image.Image:
        pad = int(self.w * self.g.medallion_padding_ratio)
        bw, bh = logo.width + 2 * pad, logo.height + 2 * pad

        medallion = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        mask = Image.new("L", (bw, bh), 0)
        md = ImageDraw.Draw(mask)
        radius = max(18, int(min(bw, bh) * self.g.medallion_corner_ratio))
        md.rounded_rectangle((0, 0, bw - 1, bh - 1), radius=radius, fill=255)

        fill_rgba = self.g.dark_medallion_fill_rgba if dark_variant else self.g.medallion_fill_rgba
        outline_rgba = self.g.dark_medallion_outline_rgba if dark_variant else self.g.medallion_outline_rgba

        fill = Image.new("RGBA", (bw, bh), fill_rgba)
        medallion = Image.composite(fill, medallion, mask)

        dd = ImageDraw.Draw(medallion)
        dd.rounded_rectangle(
            (1, 1, bw - 2, bh - 2),
            radius=radius,
            outline=outline_rgba,
            width=self.g.medallion_outline_width,
        )

        if self.g.medallion_highlight_enabled and not dark_variant:
            highlight = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
            hd = ImageDraw.Draw(highlight)
            hd.rounded_rectangle(
                (2, 2, bw - 2, int(bh * self.g.medallion_highlight_height_ratio)),
                radius=radius,
                fill=self.g.medallion_highlight_rgba,
            )
            medallion.alpha_composite(highlight)

        medallion.alpha_composite(logo, ((bw - logo.width) // 2, (bh - logo.height) // 2))
        return medallion

    def _add_center_logo(self, img: Image.Image, dark_medallion: bool = False) -> Image.Image:
        if self.cfg.logo_path is None:
            return img

        if not self.cfg.logo_path.exists():
            raise FileNotFoundError(f"Logo introuvable: {self.cfg.logo_path}")

        img = img.copy()
        logo = self._load_logo(int(self.w * self.g.logo_scale))

        if self.g.medallion_enabled:
            center_asset = self._build_medallion(logo, dark_variant=dark_medallion)
        else:
            center_asset = logo

        img.alpha_composite(center_asset, ((self.w - center_asset.width) // 2, (self.h - center_asset.height) // 2))
        return img

    # -------------------------
    # QR styling
    # -------------------------

    def _apply_dark_module_gradient(self, base_img: Image.Image) -> Image.Image:
        arr = np.array(base_img)
        rgb = arr[:, :, :3]
        dark_mask = np.max(rgb, axis=2) < 40

        grad = self._diagonal_gradient(self.w, self.h, self.g.gradient_start_rgb, self.g.gradient_end_rgb)
        grad = self._mix_gradient(grad, self.g.gradient_mix_base_rgb, self.g.gradient_mix_ratio)

        arr[dark_mask, :3] = grad[dark_mask]
        arr[:, :, 3] = 255

        finder_positions = [
            (self.offset, self.offset),
            (self.w - self.offset - 7 * self.cell, self.offset),
            (self.offset, self.h - self.offset - 7 * self.cell),
        ]
        outer = self._np_color(self.g.finder_outer_rgb)
        center = self._np_color(self.g.finder_center_rgb)

        for fx, fy in finder_positions:
            arr[fy:fy + 7 * self.cell, fx:fx + self.cell, :3] = outer
            arr[fy:fy + 7 * self.cell, fx + 6 * self.cell:fx + 7 * self.cell, :3] = outer
            arr[fy:fy + self.cell, fx:fx + 7 * self.cell, :3] = outer
            arr[fy + 6 * self.cell:fy + 7 * self.cell, fx:fx + 7 * self.cell, :3] = outer

            center_block = np.tile(center, (3 * self.cell, 3 * self.cell, 1))
            arr[fy + 2 * self.cell:fy + 5 * self.cell, fx + 2 * self.cell:fx + 5 * self.cell, :3] = center_block

        if self.g.transparent_output:
            white_mask = np.min(rgb, axis=2) > 220
            arr[white_mask, 3] = 0

        return Image.fromarray(arr, "RGBA")

    def _build_full_dark_qr(self) -> Image.Image:
        arr = np.array(self.base)
        rgb = arr[:, :, :3]
        dark_mask = np.max(rgb, axis=2) < 40

        grad = self._diagonal_gradient(
            self.w,
            self.h,
            self.g.light_module_start_rgb,
            self.g.light_module_end_rgb,
        )

        out = np.zeros((self.h, self.w, 4), dtype=np.uint8)
        out[:, :, :3] = self._np_color(self.g.background_rgba[:3])
        out[:, :, 3] = 255
        out[dark_mask, :3] = grad[dark_mask]

        finder_positions = [
            (self.offset, self.offset),
            (self.w - self.offset - 7 * self.cell, self.offset),
            (self.offset, self.h - self.offset - 7 * self.cell),
        ]
        outer = self._np_color(self.g.full_dark_finder_outer_rgb)
        center = self._np_color(self.g.full_dark_finder_center_rgb)

        for fx, fy in finder_positions:
            out[fy:fy + 7 * self.cell, fx:fx + self.cell, :3] = outer
            out[fy:fy + 7 * self.cell, fx + 6 * self.cell:fx + 7 * self.cell, :3] = outer
            out[fy:fy + self.cell, fx:fx + 7 * self.cell, :3] = outer
            out[fy + 6 * self.cell:fy + 7 * self.cell, fx:fx + 7 * self.cell, :3] = outer
            out[fy + 2 * self.cell:fy + 5 * self.cell, fx + 2 * self.cell:fx + 5 * self.cell, :3] = center

        return Image.fromarray(out, "RGBA")

    # -------------------------
    # FX
    # -------------------------

    def _apply_glow(self, img: Image.Image) -> Image.Image:
        if not self.g.glow_enabled:
            return img

        glow = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        inset = self.g.glow_inset
        gd.ellipse(
            (inset, inset, self.w - inset, self.h - inset),
            fill=self.g.glow_fill_rgba,
        )
        glow = glow.filter(ImageFilter.GaussianBlur(self.g.glow_blur_radius))
        img = img.copy()
        img.alpha_composite(glow)
        return img

    def _apply_shadow_to_image(self, img: Image.Image) -> Image.Image:
        if not self.g.shadow_enabled:
            return img

        pad = self.g.shadow_canvas_padding
        canvas = Image.new("RGBA", (img.width + pad, img.height + pad), (0, 0, 0, 0))

        alpha = np.array(img)[:, :, 3]
        shadow_mask = Image.fromarray((alpha > 0).astype(np.uint8) * 255, "L")
        shadow = Image.new("RGBA", img.size, self.g.shadow_color_rgba)

        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sh.paste(shadow, (0, 0), shadow_mask)
        sh = sh.filter(ImageFilter.GaussianBlur(self.g.shadow_blur_radius))

        dx, dy = self.g.shadow_offset
        canvas.alpha_composite(sh, (dx, dy))
        canvas.alpha_composite(img, (pad // 2, pad // 2))
        return canvas

    def _compose_on_background(self, img: Image.Image) -> Image.Image:
        if self.g.transparent_output:
            return img

        bg = Image.new("RGBA", img.size, self.g.background_rgba)
        bg.alpha_composite(img)
        return bg

    def _compose_black_bg_safe(self, qr_img: Image.Image) -> Image.Image:
        if not self.g.outer_plate_enabled:
            rendered = qr_img
            if self.g.shadow_enabled:
                rendered = self._apply_shadow_to_image(rendered)
            return self._compose_on_background(rendered)

        plate_margin = self.g.outer_plate_margin
        plate = Image.new(
            "RGBA",
            (self.w + 2 * plate_margin, self.h + 2 * plate_margin),
            self.g.plate_color_rgba,
        )
        plate.alpha_composite(qr_img, (plate_margin, plate_margin))

        if self.g.shadow_enabled:
            plate_with_shadow = self._apply_shadow_to_image(plate)
        else:
            plate_with_shadow = plate

        if self.g.transparent_output:
            return plate_with_shadow

        bg = Image.new("RGBA", plate_with_shadow.size, self.g.background_rgba)
        bg.alpha_composite(plate_with_shadow)
        return bg

    # -------------------------
    # Public API
    # -------------------------

    def render(self) -> Image.Image:
        mode = self.g.style_mode

        if mode == "black_bg_safe":
            qr_img = self._apply_dark_module_gradient(self.base)
            qr_img = self._add_center_logo(qr_img, dark_medallion=False)
            return self._compose_black_bg_safe(qr_img)

        if mode == "full_dark_artistic":
            qr_img = self._build_full_dark_qr()
            qr_img = self._apply_glow(qr_img)
            qr_img = self._add_center_logo(qr_img, dark_medallion=True)
            return qr_img

        if mode == "white_clean":
            qr_img = self._apply_dark_module_gradient(self.base)
            qr_img = self._add_center_logo(qr_img, dark_medallion=False)
            if self.g.shadow_enabled:
                qr_img = self._apply_shadow_to_image(qr_img)
            return self._compose_on_background(qr_img)

        raise ValueError(f"style_mode inconnu: {mode}")

    def save(self) -> Image.Image:
        self.cfg.output_path.parent.mkdir(parents=True, exist_ok=True)

        img = self.render()
        img.save(self.cfg.output_path)
        self._debug(f"Fichier cree : {self.cfg.output_path}")

        if self.cfg.run_decode_check:
            if cv2 is None:
                self._debug("Decodage : SKIP (opencv-python non installe)")
            else:
                decoded = self.decode_check(self.cfg.output_path)
                self._debug("Decodage :", decoded if decoded else "ECHEC")

        return img

    def decode_check(self, image_path: Path) -> str:
        if cv2 is None:
            return ""

        arr = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
        if arr is None:
            return ""

        if arr.ndim == 3 and arr.shape[2] == 4:
            alpha = arr[:, :, 3]
            rgb = arr[:, :, :3]
            bg = np.zeros((arr.shape[0], arr.shape[1], 3), dtype=np.uint8)
            bg[:] = np.array(self.g.background_rgba[:3], dtype=np.uint8)
            mask = alpha > 0
            bg[mask] = rgb[mask]
            arr = bg

        data, _, _ = cv2.QRCodeDetector().detectAndDecode(arr)
        return data if data else ""
