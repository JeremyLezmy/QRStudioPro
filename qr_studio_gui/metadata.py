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
        "Mode de rendu principal du QR (safe noir, full dark artistique, ou blanc clean).",
        "General",
    ),
    "transparent_output": FieldSpec(
        "Transparent Output",
        "Si active, le fond transparent est conserve quand le mode le permet.",
        "General",
    ),
    "background_rgba": FieldSpec(
        "Background RGBA",
        "Couleur de fond globale en RGBA.",
        "General",
    ),
    "plate_color_rgba": FieldSpec(
        "Plate RGBA",
        "Couleur de la plaque autour du QR en mode black_bg_safe.",
        "General",
    ),
    "outer_plate_enabled": FieldSpec(
        "Outer Plate",
        "Active la plaque externe qui augmente la lisibilite sur fond sombre.",
        "General",
    ),
    "outer_plate_margin": FieldSpec(
        "Outer Plate Margin",
        "Marge (en pixels) autour du QR a l'interieur de la plaque.",
        "General",
    ),
    "gradient_start_rgb": FieldSpec(
        "Gradient Start RGB",
        "Couleur de depart du gradient applique aux modules fonces.",
        "Modules",
    ),
    "gradient_end_rgb": FieldSpec(
        "Gradient End RGB",
        "Couleur de fin du gradient applique aux modules fonces.",
        "Modules",
    ),
    "gradient_mix_base_rgb": FieldSpec(
        "Gradient Mix Base",
        "Couleur de base melangee au gradient. Utiliser none pour desactiver.",
        "Modules",
    ),
    "gradient_mix_ratio": FieldSpec(
        "Gradient Mix Ratio",
        "Ratio 0..1 du melange entre base et gradient.",
        "Modules",
    ),
    "finder_outer_rgb": FieldSpec(
        "Finder Outer RGB",
        "Couleur des bords externes des marqueurs de coin.",
        "Modules",
    ),
    "finder_center_rgb": FieldSpec(
        "Finder Center RGB",
        "Couleur du centre des marqueurs de coin.",
        "Modules",
    ),
    "light_module_start_rgb": FieldSpec(
        "Light Module Start",
        "Couleur de debut pour les modules clairs en mode full dark.",
        "Full Dark",
    ),
    "light_module_end_rgb": FieldSpec(
        "Light Module End",
        "Couleur de fin pour les modules clairs en mode full dark.",
        "Full Dark",
    ),
    "full_dark_finder_outer_rgb": FieldSpec(
        "Full Dark Finder Outer",
        "Couleur du contour finder en mode full dark.",
        "Full Dark",
    ),
    "full_dark_finder_center_rgb": FieldSpec(
        "Full Dark Finder Center",
        "Couleur du centre finder en mode full dark.",
        "Full Dark",
    ),
    "logo_scale": FieldSpec(
        "Logo Scale",
        "Taille du logo relative a la largeur du QR (ex: 0.145).",
        "Logo",
    ),
    "logo_keep_original": FieldSpec(
        "Keep Logo Original",
        "Conserve le logo tel quel: pas de recolorisation et pas de suppression de fond sombre.",
        "Logo",
    ),
    "logo_remove_dark_bg": FieldSpec(
        "Remove Dark Background",
        "Rend transparentes les zones sombres du logo selon le seuil.",
        "Logo",
    ),
    "logo_dark_bg_threshold": FieldSpec(
        "Dark BG Threshold",
        "Seuil de detection de fond sombre pour le nettoyage du logo.",
        "Logo",
    ),
    "recolor_logo": FieldSpec(
        "Recolor Logo",
        "Applique un gradient de couleur au logo.",
        "Logo",
    ),
    "recolor_logo_start_rgb": FieldSpec(
        "Logo Gradient Start",
        "Couleur de debut du gradient de recolorisation du logo.",
        "Logo",
    ),
    "recolor_logo_end_rgb": FieldSpec(
        "Logo Gradient End",
        "Couleur de fin du gradient de recolorisation du logo.",
        "Logo",
    ),
    "medallion_enabled": FieldSpec(
        "Medallion Enabled",
        "Affiche une pastille autour du logo central.",
        "Medallion",
    ),
    "medallion_padding_ratio": FieldSpec(
        "Medallion Padding",
        "Espace autour du logo dans la pastille (ratio de la taille du QR).",
        "Medallion",
    ),
    "medallion_fill_rgba": FieldSpec(
        "Medallion Fill",
        "Couleur de fond de la pastille logo.",
        "Medallion",
    ),
    "medallion_outline_rgba": FieldSpec(
        "Medallion Outline",
        "Couleur du contour de la pastille logo.",
        "Medallion",
    ),
    "medallion_outline_width": FieldSpec(
        "Outline Width",
        "Epaisseur du contour de la pastille en pixels.",
        "Medallion",
    ),
    "medallion_corner_ratio": FieldSpec(
        "Corner Ratio",
        "Rayon des coins de la pastille (ratio).",
        "Medallion",
    ),
    "medallion_highlight_enabled": FieldSpec(
        "Highlight Enabled",
        "Active un reflet haut de pastille (mode clair).",
        "Medallion",
    ),
    "medallion_highlight_rgba": FieldSpec(
        "Highlight Color",
        "Couleur RGBA du reflet de pastille.",
        "Medallion",
    ),
    "medallion_highlight_height_ratio": FieldSpec(
        "Highlight Height",
        "Hauteur du reflet (ratio de la pastille).",
        "Medallion",
    ),
    "dark_medallion_fill_rgba": FieldSpec(
        "Dark Medallion Fill",
        "Fond de pastille utilise en style full dark.",
        "Medallion",
    ),
    "dark_medallion_outline_rgba": FieldSpec(
        "Dark Medallion Outline",
        "Contour de pastille utilise en style full dark.",
        "Medallion",
    ),
    "shadow_enabled": FieldSpec(
        "Shadow Enabled",
        "Active l'ombre portee globale.",
        "FX",
    ),
    "shadow_color_rgba": FieldSpec(
        "Shadow Color",
        "Couleur RGBA de l'ombre.",
        "FX",
    ),
    "shadow_blur_radius": FieldSpec(
        "Shadow Blur",
        "Rayon du flou de l'ombre.",
        "FX",
    ),
    "shadow_offset": FieldSpec(
        "Shadow Offset",
        "Decalage x,y de l'ombre (px).",
        "FX",
    ),
    "shadow_canvas_padding": FieldSpec(
        "Shadow Padding",
        "Marge supplementaire pour ne pas couper l'ombre.",
        "FX",
    ),
    "glow_enabled": FieldSpec(
        "Glow Enabled",
        "Active un halo lumineux autour du QR.",
        "FX",
    ),
    "glow_fill_rgba": FieldSpec(
        "Glow Color",
        "Couleur RGBA du halo.",
        "FX",
    ),
    "glow_blur_radius": FieldSpec(
        "Glow Blur",
        "Rayon de flou du halo.",
        "FX",
    ),
    "glow_inset": FieldSpec(
        "Glow Inset",
        "Inset du halo par rapport au bord de l'image.",
        "FX",
    ),
}


GROUP_ORDER = ["General", "Modules", "Full Dark", "Logo", "Medallion", "FX"]


def get_field_spec(field_name: str) -> Optional[FieldSpec]:
    return FIELD_SPECS.get(field_name)
