from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple, Optional, Dict

import numpy as np
import cv2
import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image, ImageDraw, ImageFilter


# =========================================================
# CONFIG MODELS
# =========================================================

Color3 = Tuple[int, int, int]
Color4 = Tuple[int, int, int, int]


@dataclass
class QRConfig:
    # Core content
    url: str = "https://phusis.io/"
    logo_path: Path = Path("logo.png")
    output_path: Path = Path("qr_output.png")

    # QR technical settings
    error_correction: int = ERROR_CORRECT_H
    box_size: int = 22
    border: int = 4

    # Main rendering mode
    # "black_bg_safe"      -> fond noir global + plaque blanche fiable
    # "full_dark_artistic" -> full dark esthétique, potentiellement moins fiable
    style_mode: str = "black_bg_safe"

    # Canvas / background
    background_rgba: Color4 = (8, 10, 14, 255)
    plate_color_rgba: Color4 = (255, 255, 255, 255)
    transparent_output: bool = False

    # QR dark-module styling
    gradient_start_rgb: Color3 = (16, 72, 62)
    gradient_end_rgb: Color3 = (36, 92, 132)
    gradient_mix_base_rgb: Optional[Color3] = (16, 21, 28)
    gradient_mix_ratio: float = 0.55  # 0..1 applied to mix_base

    # Finder styling
    finder_outer_rgb: Color3 = (16, 21, 28)
    finder_center_rgb: Color3 = (26, 130, 118)

    # For inverted / full-dark modes
    light_module_start_rgb: Color3 = (214, 240, 236)
    light_module_end_rgb: Color3 = (90, 180, 200)
    full_dark_finder_outer_rgb: Color3 = (232, 248, 245)
    full_dark_finder_center_rgb: Color3 = (170, 220, 228)

    # Logo
    logo_scale: float = 0.145           # relative to QR width
    logo_remove_dark_bg: bool = True
    logo_dark_bg_threshold: int = 18
    recolor_logo: bool = True
    recolor_logo_start_rgb: Color3 = (38, 170, 150)
    recolor_logo_end_rgb: Color3 = (70, 120, 165)

    # Logo medallion
    medallion_enabled: bool = True
    medallion_padding_ratio: float = 0.018
    medallion_fill_rgba: Color4 = (250, 251, 252, 255)
    medallion_outline_rgba: Color4 = (228, 232, 238, 255)
    medallion_outline_width: int = 2
    medallion_corner_ratio: float = 0.22
    medallion_highlight_enabled: bool = False
    medallion_highlight_rgba: Color4 = (255, 255, 255, 36)
    medallion_highlight_height_ratio: float = 0.42

    # Dark medallion option for full dark styles
    dark_medallion_fill_rgba: Color4 = (18, 24, 30, 245)
    dark_medallion_outline_rgba: Color4 = (210, 232, 230, 180)

    # White plate around QR (safe black background mode)
    outer_plate_enabled: bool = True
    outer_plate_margin: int = 56

    # Shadow
    shadow_enabled: bool = True
    shadow_color_rgba: Color4 = (0, 0, 0, 90)
    shadow_blur_radius: int = 14
    shadow_offset: Tuple[int, int] = (20, 24)
    shadow_canvas_padding: int = 40

    # Glow / vignette
    glow_enabled: bool = False
    glow_fill_rgba: Color4 = (40, 130, 120, 18)
    glow_blur_radius: int = 40
    glow_inset: int = 80

    # Decode check
    run_decode_check: bool = True
    verbose: bool = True


# =========================================================
# PRESETS
# =========================================================

PRESETS: Dict[str, Dict] = {
    "black_bg_safe": {
        "style_mode": "black_bg_safe",
        "background_rgba": (8, 10, 14, 255),
        "plate_color_rgba": (255, 255, 255, 255),
        "outer_plate_enabled": True,
        "shadow_enabled": True,
        "glow_enabled": False,
        "recolor_logo": True,
        "medallion_enabled": True,
        "medallion_fill_rgba": (250, 251, 252, 255),
        "medallion_outline_rgba": (228, 232, 238, 255),
        "medallion_highlight_enabled": False,
    },
    "full_dark_artistic": {
        "style_mode": "full_dark_artistic",
        "background_rgba": (8, 10, 14, 255),
        "outer_plate_enabled": False,
        "shadow_enabled": False,
        "glow_enabled": True,
        "recolor_logo": False,
        "medallion_enabled": True,
        "dark_medallion_fill_rgba": (18, 24, 30, 245),
        "dark_medallion_outline_rgba": (210, 232, 230, 180),
    },
    "white_clean": {
        "style_mode": "white_clean",
        "background_rgba": (255, 255, 255, 255),
        "outer_plate_enabled": False,
        "shadow_enabled": False,
        "glow_enabled": False,
        "recolor_logo": True,
        "medallion_enabled": True,
        "medallion_fill_rgba": (250, 251, 252, 255),
        "medallion_outline_rgba": (228, 232, 238, 255),
    },
}


def apply_preset(base: QRConfig, preset_name: Optional[str]) -> QRConfig:
    if not preset_name:
        return base
    if preset_name not in PRESETS:
        raise ValueError(f"Preset inconnu: {preset_name}. Disponibles: {list(PRESETS)}")
    data = PRESETS[preset_name]
    for k, v in data.items():
        setattr(base, k, v)
    return base


# =========================================================
# GENERATOR
# =========================================================

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

    # -------------------------
    # Utility
    # -------------------------

    @staticmethod
    def _np_color(c: Color3) -> np.ndarray:
        return np.array(c, dtype=np.uint8)

    @staticmethod
    def _ensure_rgba(im: Image.Image) -> Image.Image:
        return im if im.mode == "RGBA" else im.convert("RGBA")

    def _diagonal_gradient(self, w: int, h: int, c1: Color3, c2: Color3) -> np.ndarray:
        a = self._np_color(c1)
        b = self._np_color(c2)
        yy, xx = np.indices((h, w))
        t = ((xx + yy) / max(1, (w + h))).astype(np.float32)[..., None]
        return ((1 - t) * a + t * b).astype(np.uint8)

    def _mix_gradient(self, grad: np.ndarray, base_rgb: Optional[Color3], ratio: float) -> np.ndarray:
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
        img = Image.open(self.cfg.logo_path).convert("RGBA")
        arr = np.array(img)

        if self.cfg.logo_remove_dark_bg:
            rgb = arr[:, :, :3].astype(np.int16)
            dark = np.max(rgb, axis=2) < self.cfg.logo_dark_bg_threshold
            arr[dark, 3] = 0

        alpha = arr[:, :, 3]
        ys, xs = np.where(alpha > 0)
        if len(xs):
            arr = arr[ys.min():ys.max() + 1, xs.min():xs.max() + 1]

        if self.cfg.recolor_logo:
            alpha_mask = arr[:, :, 3] > 0
            yy, xx = np.indices(arr.shape[:2])
            t = ((xx + yy) / max(1, arr.shape[0] + arr.shape[1])).astype(np.float32)[..., None]
            c1 = self._np_color(self.cfg.recolor_logo_start_rgb)
            c2 = self._np_color(self.cfg.recolor_logo_end_rgb)
            grad = ((1 - t) * c1 + t * c2).astype(np.uint8)
            arr[alpha_mask, :3] = grad[alpha_mask]

        logo = Image.fromarray(arr, "RGBA")
        scale = target_w / max(logo.size)
        return logo.resize(
            (max(1, int(logo.width * scale)), max(1, int(logo.height * scale))),
            Image.LANCZOS,
        )

    def _build_medallion(self, logo: Image.Image, dark_variant: bool = False) -> Image.Image:
        pad = int(self.w * self.cfg.medallion_padding_ratio)
        bw, bh = logo.width + 2 * pad, logo.height + 2 * pad

        medallion = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        mask = Image.new("L", (bw, bh), 0)
        md = ImageDraw.Draw(mask)
        radius = max(18, int(min(bw, bh) * self.cfg.medallion_corner_ratio))
        md.rounded_rectangle((0, 0, bw - 1, bh - 1), radius=radius, fill=255)

        fill_rgba = self.cfg.dark_medallion_fill_rgba if dark_variant else self.cfg.medallion_fill_rgba
        outline_rgba = self.cfg.dark_medallion_outline_rgba if dark_variant else self.cfg.medallion_outline_rgba

        fill = Image.new("RGBA", (bw, bh), fill_rgba)
        medallion = Image.composite(fill, medallion, mask)

        dd = ImageDraw.Draw(medallion)
        dd.rounded_rectangle(
            (1, 1, bw - 2, bh - 2),
            radius=radius,
            outline=outline_rgba,
            width=self.cfg.medallion_outline_width,
        )

        if self.cfg.medallion_highlight_enabled and not dark_variant:
            highlight = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
            hd = ImageDraw.Draw(highlight)
            hd.rounded_rectangle(
                (2, 2, bw - 2, int(bh * self.cfg.medallion_highlight_height_ratio)),
                radius=radius,
                fill=self.cfg.medallion_highlight_rgba,
            )
            medallion.alpha_composite(highlight)

        medallion.alpha_composite(logo, ((bw - logo.width) // 2, (bh - logo.height) // 2))
        return medallion

    def _add_center_logo(self, img: Image.Image, dark_medallion: bool = False) -> Image.Image:
        if not self.cfg.medallion_enabled:
            return img

        img = img.copy()
        logo = self._load_logo(int(self.w * self.cfg.logo_scale))
        medallion = self._build_medallion(logo, dark_variant=dark_medallion)
        img.alpha_composite(medallion, ((self.w - medallion.width) // 2, (self.h - medallion.height) // 2))
        return img

    # -------------------------
    # QR styling
    # -------------------------

    def _apply_dark_module_gradient(self, base_img: Image.Image) -> Image.Image:
        arr = np.array(base_img)
        rgb = arr[:, :, :3]
        dark_mask = np.max(rgb, axis=2) < 40

        grad = self._diagonal_gradient(self.w, self.h, self.cfg.gradient_start_rgb, self.cfg.gradient_end_rgb)
        grad = self._mix_gradient(grad, self.cfg.gradient_mix_base_rgb, self.cfg.gradient_mix_ratio)

        arr[dark_mask, :3] = grad[dark_mask]
        arr[:, :, 3] = 255

        finder_positions = [
            (self.offset, self.offset),
            (self.w - self.offset - 7 * self.cell, self.offset),
            (self.offset, self.h - self.offset - 7 * self.cell),
        ]
        outer = self._np_color(self.cfg.finder_outer_rgb)
        center = self._np_color(self.cfg.finder_center_rgb)

        for fx, fy in finder_positions:
            arr[fy:fy + 7 * self.cell, fx:fx + self.cell, :3] = outer
            arr[fy:fy + 7 * self.cell, fx + 6 * self.cell:fx + 7 * self.cell, :3] = outer
            arr[fy:fy + self.cell, fx:fx + 7 * self.cell, :3] = outer
            arr[fy + 6 * self.cell:fy + 7 * self.cell, fx:fx + 7 * self.cell, :3] = outer

            center_block = np.tile(center, (3 * self.cell, 3 * self.cell, 1))
            arr[fy + 2 * self.cell:fy + 5 * self.cell, fx + 2 * self.cell:fx + 5 * self.cell, :3] = center_block

        if self.cfg.transparent_output:
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
            self.cfg.light_module_start_rgb,
            self.cfg.light_module_end_rgb,
        )

        out = np.zeros((self.h, self.w, 4), dtype=np.uint8)
        out[:, :, :3] = self._np_color(self.cfg.background_rgba[:3])
        out[:, :, 3] = 255
        out[dark_mask, :3] = grad[dark_mask]

        finder_positions = [
            (self.offset, self.offset),
            (self.w - self.offset - 7 * self.cell, self.offset),
            (self.offset, self.h - self.offset - 7 * self.cell),
        ]
        outer = self._np_color(self.cfg.full_dark_finder_outer_rgb)
        center = self._np_color(self.cfg.full_dark_finder_center_rgb)

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
        if not self.cfg.glow_enabled:
            return img
        glow = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        inset = self.cfg.glow_inset
        gd.ellipse(
            (inset, inset, self.w - inset, self.h - inset),
            fill=self.cfg.glow_fill_rgba,
        )
        glow = glow.filter(ImageFilter.GaussianBlur(self.cfg.glow_blur_radius))
        img = img.copy()
        img.alpha_composite(glow)
        return img

    def _apply_shadow_to_image(self, img: Image.Image) -> Image.Image:
        if not self.cfg.shadow_enabled:
            return img

        pad = self.cfg.shadow_canvas_padding
        canvas = Image.new("RGBA", (img.width + pad, img.height + pad), (0, 0, 0, 0))

        alpha = np.array(img)[:, :, 3]
        shadow_mask = Image.fromarray((alpha > 0).astype(np.uint8) * 255, "L")
        shadow = Image.new("RGBA", img.size, self.cfg.shadow_color_rgba)

        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sh.paste(shadow, (0, 0), shadow_mask)
        sh = sh.filter(ImageFilter.GaussianBlur(self.cfg.shadow_blur_radius))

        dx, dy = self.cfg.shadow_offset
        canvas.alpha_composite(sh, (dx, dy))
        canvas.alpha_composite(img, (pad // 2, pad // 2))
        return canvas

    def _compose_on_background(self, img: Image.Image) -> Image.Image:
        if self.cfg.transparent_output:
            return img

        bg = Image.new("RGBA", img.size, self.cfg.background_rgba)
        bg.alpha_composite(img)
        return bg

    def _compose_black_bg_safe(self, qr_img: Image.Image) -> Image.Image:
        plate_margin = self.cfg.outer_plate_margin
        plate = Image.new(
            "RGBA",
            (self.w + 2 * plate_margin, self.h + 2 * plate_margin),
            self.cfg.plate_color_rgba,
        )
        plate.alpha_composite(qr_img, (plate_margin, plate_margin))

        if self.cfg.shadow_enabled:
            plate_with_shadow = self._apply_shadow_to_image(plate)
        else:
            plate_with_shadow = plate

        if self.cfg.transparent_output:
            return plate_with_shadow

        bg = Image.new("RGBA", plate_with_shadow.size, self.cfg.background_rgba)
        bg.alpha_composite(plate_with_shadow)
        return bg

    # -------------------------
    # Public API
    # -------------------------

    def render(self) -> Image.Image:
        mode = self.cfg.style_mode

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
            if self.cfg.shadow_enabled:
                qr_img = self._apply_shadow_to_image(qr_img)
            return self._compose_on_background(qr_img)

        raise ValueError(f"style_mode inconnu: {mode}")

    def save(self) -> Image.Image:
        img = self.render()
        img.save(self.cfg.output_path)
        self._debug(f"Fichier créé : {self.cfg.output_path}")

        if self.cfg.run_decode_check:
            decoded = self.decode_check(self.cfg.output_path)
            self._debug("Décodage :", decoded if decoded else "ECHEC")

        return img

    def decode_check(self, image_path: Path) -> str:
        arr = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
        if arr is None:
            return ""

        if arr.shape[2] == 4:
            alpha = arr[:, :, 3]
            rgb = arr[:, :, :3]
            bg = np.zeros((arr.shape[0], arr.shape[1], 3), dtype=np.uint8)
            bg[:] = np.array(self.cfg.background_rgba[:3], dtype=np.uint8)
            mask = alpha > 0
            bg[mask] = rgb[mask]
            arr = bg

        data, _, _ = cv2.QRCodeDetector().detectAndDecode(arr)
        return data if data else ""


# =========================================================
# EXAMPLES
# =========================================================

if __name__ == "__main__":
    # -----------------------------------------------------
    # EXEMPLE 1: version fiable sur fond noir
    # -----------------------------------------------------
    cfg1 = apply_preset(
        QRConfig(
            url="https://phusis.io/",
            logo_path=Path("logo_phusis.png"),
            output_path=Path("generated_qrcode/phusis_black_bg_safe.png"),
        ),
        "black_bg_safe",
    )
    BrandedQRGenerator(cfg1).save()

    # -----------------------------------------------------
    # EXEMPLE 2: version full dark artistique
    # -----------------------------------------------------
    cfg2 = apply_preset(
        QRConfig(
            url="https://phusis.io/",
            logo_path=Path("logo_phusis.png"),
            output_path=Path("generated_qrcode/phusis_full_dark_artistic.png"),
        ),
        "full_dark_artistic",
    )
    BrandedQRGenerator(cfg2).save()

    # -----------------------------------------------------
    # EXEMPLE 3: variation custom
    # -----------------------------------------------------
    cfg3 = apply_preset(
        QRConfig(
            url="https://example.com/",
            logo_path=Path("logo_phusis.png"),
            output_path=Path("generated_qrcode/phusis_custom.png"),
        ),
        "black_bg_safe",
    )

    # Variations graphiques futures
    cfg3.gradient_start_rgb = (10, 110, 95)
    cfg3.gradient_end_rgb = (55, 95, 150)
    cfg3.finder_center_rgb = (40, 170, 150)
    cfg3.logo_scale = 0.13
    cfg3.outer_plate_margin = 64
    cfg3.medallion_highlight_enabled = True
    cfg3.medallion_fill_rgba = (252, 252, 253, 255)

    BrandedQRGenerator(cfg3).save()