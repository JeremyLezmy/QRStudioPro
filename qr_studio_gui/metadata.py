from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class FieldSpec:
    label: str
    description: str
    group: str


FIELD_SPECS: Dict[str, FieldSpec] = {
    "style_mode": FieldSpec(
        "Style Mode",
        "Mode de rendu principal du QR : 'black_bg_safe' (fond noir + plaque blanche, le plus fiable pour le scan), "
        "'full_dark_artistic' (rendu sombre esthétique), ou 'white_clean' (fond blanc épuré).",
        "General",
    ),
    "transparent_output": FieldSpec(
        "Transparent",
        "Si activé, le fond est transparent (utile pour intégrer le QR sur un visuel existant). "
        "Non compatible avec tous les modes.",
        "General",
    ),
    "background_rgba": FieldSpec(
        "Background",
        "Couleur de fond globale (R, G, B, A). Ignorée si 'Transparent' est activé.",
        "General",
    ),
    "plate_color_rgba": FieldSpec(
        "Plate Color",
        "Couleur de la plaque blanche entourant le QR en mode 'black_bg_safe'. "
        "Améliore la lisibilité sur fond sombre.",
        "General",
    ),
    "outer_plate_enabled": FieldSpec(
        "Outer Plate",
        "Active la plaque externe autour du QR. Recommandé en mode 'black_bg_safe' "
        "pour garantir la lisibilité du QR par les scanners.",
        "General",
    ),
    "outer_plate_margin": FieldSpec(
        "Plate Margin",
        "Marge en pixels entre le QR et le bord de la plaque. "
        "Valeur typique : 40–80 px.",
        "General",
    ),
    "gradient_start_rgb": FieldSpec(
        "Gradient Start",
        "Couleur de départ du dégradé diagonal appliqué aux modules sombres du QR. "
        "Format : R, G, B (0–255).",
        "Modules",
    ),
    "gradient_end_rgb": FieldSpec(
        "Gradient End",
        "Couleur de fin du dégradé diagonal. Le gradient va du coin haut-gauche "
        "vers le coin bas-droit.",
        "Modules",
    ),
    "gradient_mix_base_rgb": FieldSpec(
        "Mix Base",
        "Couleur de base mélangée au gradient pour l'atténuer. "
        "Écrire 'none' pour désactiver le mélange.",
        "Modules",
    ),
    "gradient_mix_ratio": FieldSpec(
        "Mix Ratio",
        "Proportion du mélange : 0.0 = 100%% gradient pur, 1.0 = 100%% couleur de base. "
        "Valeur typique : 0.4–0.6.",
        "Modules",
    ),
    "module_shape": FieldSpec(
        "Module Shape",
        "Forme des modules internes du QR: square, rounded, ou dot.",
        "Modules",
    ),
    "module_scale": FieldSpec(
        "Module Scale",
        "Taille relative des modules (1.0 = pleine case, <1.0 = plus petit et plus aéré).",
        "Modules",
    ),
    "module_corner_ratio": FieldSpec(
        "Corner Ratio",
        "Rayon des coins pour les modules rounded (0.0 carré, 1.0 très arrondi).",
        "Modules",
    ),
    "finder_outer_rgb": FieldSpec(
        "Finder Outer",
        "Couleur des bords externes des 3 marqueurs de coin (carrés de repérage). "
        "Couleur unie, pas de gradient.",
        "Modules",
    ),
    "finder_center_rgb": FieldSpec(
        "Finder Center",
        "Couleur du carré central des 3 marqueurs de coin.",
        "Modules",
    ),
    "light_module_start_rgb": FieldSpec(
        "Light Start",
        "Couleur de début des modules clairs en mode Full Dark. "
        "En Full Dark, les rôles sont inversés : les modules 'clairs' portent le gradient.",
        "Full Dark",
    ),
    "light_module_end_rgb": FieldSpec(
        "Light End",
        "Couleur de fin des modules clairs en mode Full Dark.",
        "Full Dark",
    ),
    "full_dark_finder_outer_rgb": FieldSpec(
        "FD Finder Outer",
        "Couleur du contour des marqueurs de coin en mode Full Dark.",
        "Full Dark",
    ),
    "full_dark_finder_center_rgb": FieldSpec(
        "FD Finder Center",
        "Couleur du centre des marqueurs de coin en mode Full Dark.",
        "Full Dark",
    ),
    "logo_scale": FieldSpec(
        "Logo Scale",
        "Taille du logo relative à la largeur du QR. "
        "Ex : 0.145 ≈ 14.5%% de la largeur. Trop grand peut empêcher le scan.",
        "Logo",
    ),
    "logo_keep_original": FieldSpec(
        "Keep Original",
        "Conserve le logo tel quel : pas de recolorisation, pas de suppression de fond sombre. "
        "Utile pour les logos avec des couleurs précises (ex : photo, logo multicolore).",
        "Logo",
    ),
    "logo_remove_dark_bg": FieldSpec(
        "Remove Dark BG",
        "Rend transparentes les zones sombres du logo (en dessous du seuil). "
        "Utile pour les logos sur fond noir.",
        "Logo",
    ),
    "logo_dark_bg_threshold": FieldSpec(
        "Dark Threshold",
        "Seuil de luminosité (0–255) pour détecter le fond sombre du logo. "
        "Pixels plus sombres que ce seuil deviennent transparents.",
        "Logo",
    ),
    "recolor_logo": FieldSpec(
        "Recolor Logo",
        "Applique un dégradé de couleur au logo pour l'harmoniser avec le thème du QR. "
        "Désactivé automatiquement si 'Keep Original' est activé.",
        "Logo",
    ),
    "recolor_logo_start_rgb": FieldSpec(
        "Recolor Start",
        "Couleur de début du gradient de recolorisation du logo.",
        "Logo",
    ),
    "recolor_logo_end_rgb": FieldSpec(
        "Recolor End",
        "Couleur de fin du gradient de recolorisation du logo.",
        "Logo",
    ),
    "medallion_enabled": FieldSpec(
        "Medallion",
        "Affiche une pastille (cadre arrondi) autour du logo central. "
        "Améliore la lisibilité du logo sur le QR.",
        "Medallion",
    ),
    "medallion_padding_ratio": FieldSpec(
        "Padding",
        "Espace autour du logo dans la pastille, en ratio de la taille du QR. "
        "Ex : 0.018 ≈ 1.8%% d'espace.",
        "Medallion",
    ),
    "medallion_fill_rgba": FieldSpec(
        "Fill Color",
        "Couleur de fond de la pastille (R, G, B, A).",
        "Medallion",
    ),
    "medallion_outline_rgba": FieldSpec(
        "Outline Color",
        "Couleur du contour de la pastille (R, G, B, A).",
        "Medallion",
    ),
    "medallion_outline_width": FieldSpec(
        "Outline Width",
        "Épaisseur du contour de la pastille en pixels. Valeur typique : 1–3 px.",
        "Medallion",
    ),
    "medallion_corner_ratio": FieldSpec(
        "Corner Ratio",
        "Rayon des coins arrondis de la pastille en ratio. "
        "0.0 = carré, 0.5 = cercle parfait.",
        "Medallion",
    ),
    "medallion_highlight_enabled": FieldSpec(
        "Highlight",
        "Active un reflet lumineux en haut de la pastille (effet glossy). "
        "Fonctionne uniquement en mode clair.",
        "Medallion",
    ),
    "medallion_highlight_rgba": FieldSpec(
        "Highlight Color",
        "Couleur RGBA du reflet. L'alpha contrôle l'intensité du reflet.",
        "Medallion",
    ),
    "medallion_highlight_height_ratio": FieldSpec(
        "Highlight Height",
        "Hauteur du reflet en ratio de la pastille. Ex : 0.42 = reflet couvre 42%% du haut.",
        "Medallion",
    ),
    "dark_medallion_fill_rgba": FieldSpec(
        "Dark Fill",
        "Couleur de fond de la pastille en mode Full Dark. "
        "Typiquement sombre pour s'intégrer au thème.",
        "Medallion",
    ),
    "dark_medallion_outline_rgba": FieldSpec(
        "Dark Outline",
        "Couleur du contour de la pastille en mode Full Dark.",
        "Medallion",
    ),
    "shadow_enabled": FieldSpec(
        "Shadow",
        "Active une ombre portée sous le QR code pour un effet de profondeur.",
        "FX",
    ),
    "shadow_color_rgba": FieldSpec(
        "Shadow Color",
        "Couleur de l'ombre (R, G, B, A). L'alpha contrôle l'opacité de l'ombre.",
        "FX",
    ),
    "shadow_blur_radius": FieldSpec(
        "Shadow Blur",
        "Rayon du flou gaussien de l'ombre en pixels. Plus élevé = ombre plus douce.",
        "FX",
    ),
    "shadow_offset": FieldSpec(
        "Shadow Offset",
        "Décalage x, y de l'ombre en pixels. Simule la direction de la lumière.",
        "FX",
    ),
    "shadow_canvas_padding": FieldSpec(
        "Shadow Padding",
        "Marge supplémentaire autour de l'image pour ne pas couper l'ombre. "
        "Doit être ≥ blur_radius + max(offset).",
        "FX",
    ),
    "glow_enabled": FieldSpec(
        "Glow",
        "Active un halo lumineux autour du QR. "
        "Principalement utilisé en mode Full Dark Artistic.",
        "FX",
    ),
    "glow_fill_rgba": FieldSpec(
        "Glow Color",
        "Couleur RGBA du halo lumineux. L'alpha contrôle l'intensité.",
        "FX",
    ),
    "glow_blur_radius": FieldSpec(
        "Glow Blur",
        "Rayon de flou du halo en pixels. Plus élevé = halo plus diffus.",
        "FX",
    ),
    "glow_inset": FieldSpec(
        "Glow Inset",
        "Distance en pixels entre le bord de l'image et le début du halo. "
        "Plus élevé = halo plus petit et centré.",
        "FX",
    ),
}


GROUP_ORDER = ["General", "Modules", "Full Dark", "Logo", "Medallion", "FX"]


def get_field_spec(field_name: str) -> Optional[FieldSpec]:
    return FIELD_SPECS.get(field_name)
