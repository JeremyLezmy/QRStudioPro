from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import copy
import json

Color3 = Tuple[int, int, int]
Color4 = Tuple[int, int, int, int]


@dataclass
class GraphicConfig:
    # Main rendering mode
    # "black_bg_safe"      -> fond noir global + plaque blanche fiable
    # "full_dark_artistic" -> full dark esthetique, potentiellement moins fiable
    # "white_clean"        -> rendu clair, propre et lisible
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
    logo_scale: float = 0.145  # relative to QR width
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


PRESET_OVERRIDES: Dict[str, Dict[str, Any]] = {
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
    "luxury": {
        "style_mode": "black_bg_safe",
        "background_rgba": (12, 10, 8, 255),
        "plate_color_rgba": (247, 239, 225, 255),
        "gradient_start_rgb": (123, 88, 25),
        "gradient_end_rgb": (197, 152, 67),
        "gradient_mix_base_rgb": (40, 28, 11),
        "gradient_mix_ratio": 0.4,
        "finder_outer_rgb": (65, 48, 20),
        "finder_center_rgb": (209, 167, 85),
        "recolor_logo": True,
        "recolor_logo_start_rgb": (150, 112, 41),
        "recolor_logo_end_rgb": (220, 183, 97),
        "medallion_fill_rgba": (253, 247, 236, 255),
        "medallion_outline_rgba": (216, 184, 124, 255),
        "shadow_enabled": True,
        "glow_enabled": False,
    },
    # Preset inspire du site https://pena-psychologue.com/
    "pena_psychologue": {
        "style_mode": "white_clean",
        "background_rgba": (246, 240, 233, 255),
        "gradient_start_rgb": (98, 118, 107),
        "gradient_end_rgb": (177, 144, 121),
        "gradient_mix_base_rgb": (58, 65, 60),
        "gradient_mix_ratio": 0.45,
        "finder_outer_rgb": (77, 88, 82),
        "finder_center_rgb": (165, 124, 100),
        "recolor_logo": True,
        "recolor_logo_start_rgb": (108, 135, 122),
        "recolor_logo_end_rgb": (175, 139, 114),
        "medallion_fill_rgba": (252, 248, 243, 255),
        "medallion_outline_rgba": (220, 202, 187, 255),
        "shadow_enabled": True,
        "shadow_color_rgba": (35, 35, 35, 55),
        "shadow_blur_radius": 10,
        "shadow_offset": (8, 10),
        "shadow_canvas_padding": 22,
    },
}


def list_presets() -> list[str]:
    return sorted(PRESET_OVERRIDES.keys())


def _coerce_override_value(current_value: Any, override_value: Any) -> Any:
    if isinstance(current_value, tuple) and isinstance(override_value, list):
        return tuple(override_value)
    return override_value


def apply_graphic_overrides(config: GraphicConfig, overrides: Dict[str, Any]) -> GraphicConfig:
    allowed_fields = {f.name for f in fields(GraphicConfig)}
    for key, value in overrides.items():
        if key not in allowed_fields:
            raise ValueError(f"Champ graphique inconnu: {key}")
        current = getattr(config, key)
        setattr(config, key, _coerce_override_value(current, value))
    return config


def get_preset_graphic_config(preset_name: Optional[str]) -> GraphicConfig:
    config = GraphicConfig()
    if not preset_name:
        return config

    if preset_name not in PRESET_OVERRIDES:
        raise ValueError(
            f"Preset inconnu: {preset_name}. Disponibles: {list_presets()}"
        )

    return apply_graphic_overrides(config, copy.deepcopy(PRESET_OVERRIDES[preset_name]))


def load_graphic_overrides(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Le fichier de config graphique doit contenir un objet JSON")
    return data
