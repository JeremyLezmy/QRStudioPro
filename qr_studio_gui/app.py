from __future__ import annotations

import copy
import sys
from dataclasses import fields
from pathlib import Path
from typing import Any, Dict, Optional

import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, simpledialog

try:
    import customtkinter as ctk
except ModuleNotFoundError as exc:
    raise SystemExit(
        "customtkinter est requis. Installe-le avec: pip install customtkinter"
    ) from exc

from PIL import Image

from generate_qrcode import BrandedQRGenerator, create_qr_config
from qr_presets import (
    GraphicConfig,
    apply_graphic_overrides,
    get_preset_graphic_config,
    list_presets,
    load_graphic_preset,
    save_graphic_preset,
)
from qr_studio_gui.metadata import GROUP_ORDER, get_field_spec
from qr_studio_gui.tooltips import ToolTip

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ModuleNotFoundError:
    DND_FILES = None
    TkinterDnD = None

STYLE_MODE_VALUES = ["black_bg_safe", "full_dark_artistic", "white_clean"]
OPTIONAL_TUPLE_FIELDS = {"gradient_mix_base_rgb"}
LEFT_PANEL_WEIGHT = 7
RIGHT_PANEL_WEIGHT = 5
LEFT_PANEL_MIN_WIDTH = 540
RIGHT_PANEL_MIN_WIDTH = 360
WINDOW_MIN_WIDTH = 1120
WINDOW_MIN_HEIGHT = 760
RIGHT_PANEL_RATIO_MIN = 0.28
RIGHT_PANEL_RATIO_MAX = 0.62
BUILTIN_LOGO_TOKEN_PREFIX = "builtin:"


class QrStudioApp:
    def __init__(self, root: tk.Misc):
        self.root = root
        self.root.title("QR Studio Pro")
        self.root.geometry("1600x940")
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self._window_icon_photo: Optional[tk.PhotoImage] = None
        self._set_application_icon()
        self._builtin_logo_paths = self._discover_builtin_logos()
        self._logo_library_sync_lock = False

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        self._builtin_preset_names = list_presets()
        self._custom_presets: Dict[str, Dict[str, Any]] = {}

        initial_preset = "black_bg_safe"
        if initial_preset not in self._builtin_preset_names and self._builtin_preset_names:
            initial_preset = self._builtin_preset_names[0]

        self.url_var = tk.StringVar(value="https://phusis.io/")
        self.preset_var = tk.StringVar(value=initial_preset)
        self.preview_split_ratio_var = tk.DoubleVar(
            value=RIGHT_PANEL_WEIGHT / max(1.0, (LEFT_PANEL_WEIGHT + RIGHT_PANEL_WEIGHT))
        )
        self.preview_split_text_var = tk.StringVar()
        self.logo_var = tk.StringVar(value=self._default_logo_path())
        self.logo_library_var = tk.StringVar(value="Custom")
        self.output_var = tk.StringVar(value="generated_qrcode/qr_output.png")
        self.box_size_var = tk.StringVar(value="22")
        self.border_var = tk.StringVar(value="4")
        self.output_format_var = tk.StringVar(value="auto")
        self.output_quality_var = tk.IntVar(value=92)
        self.output_max_width_var = tk.StringVar(value="")

        self.auto_preview_var = tk.BooleanVar(value=True)
        self.decode_var = tk.BooleanVar(value=True)
        self.quiet_var = tk.BooleanVar(value=False)

        self.graphic_vars: Dict[str, tk.Variable] = {}
        self.tooltips: list[ToolTip] = []
        self.color_swatches: Dict[str, ctk.CTkFrame] = {}
        self._export_quality_widgets: list[tk.Widget] = []
        self._export_maxw_widgets: list[tk.Widget] = []

        self._preview_job_id: Optional[str] = None
        self._resize_preview_job_id: Optional[str] = None
        self._suspend_auto_preview = False
        self._preview_ctk_image: Optional[ctk.CTkImage] = None
        self._last_rendered_image: Optional[Image.Image] = None
        self._preview_source_image: Optional[Image.Image] = None
        self._last_preview_size: tuple[int, int] = (0, 0)
        self._last_preview_render_size: tuple[int, int] = (0, 0)
        self._last_root_size: tuple[int, int] = (0, 0)
        self._window_transform_end_job: Optional[str] = None
        self._layout_lock_active = False
        self.group_input_widgets: Dict[str, list[tk.Widget]] = {name: [] for name in GROUP_ORDER}
        self.full_dark_hint_label: Optional[ctk.CTkLabel] = None

        self._build_ui()
        self._apply_layout_split_ratio(self.preview_split_ratio_var.get())
        self._load_preset(self.preset_var.get())
        self._register_var_watchers()
        self._sync_logo_library_selection()
        if self.preset_var.get().strip() == "black_bg_safe":
            self._apply_logo_recommended_preset(self.logo_library_var.get(), show_status=False)

        self.root.bind("<Configure>", self._on_root_configure, add=True)
        self.preview_image_label.bind("<Configure>", self._on_preview_container_resize, add=True)
        self._schedule_auto_preview()

    def _default_logo_path(self) -> str:
        if "Phusis" in self._builtin_logo_paths:
            return self._builtin_logo_token_for_label("Phusis")
        return ""

    def _discover_builtin_logos(self) -> Dict[str, Optional[Path]]:
        root = self._project_root()

        def _pick(*relative_paths: str) -> Optional[Path]:
            for rel in relative_paths:
                p = root / rel
                if p.exists():
                    return p
            return None

        logos: Dict[str, Optional[Path]] = {"No logo": None}

        phusis = _pick("assets/logos/logo_phusis.png", "logo_phusis.png")
        if phusis is not None:
            logos["Phusis"] = phusis

        romane = _pick(
            "assets/logos/logo-romane-pena.webp",
            "assets/logos/logo-romane-pena.png",
            "logo-romane-pena.webp",
            "logo-romane-pena.png",
        )
        if romane is not None:
            logos["Romane Pena"] = romane

        return logos

    def _logo_library_values(self) -> list[str]:
        return ["Custom"] + list(self._builtin_logo_paths.keys())

    @staticmethod
    def _builtin_logo_token_for_label(label: str) -> str:
        if label == "No logo":
            return "none"
        slug = (
            label.strip()
            .lower()
            .replace(" ", "_")
            .replace("-", "_")
        )
        return f"{BUILTIN_LOGO_TOKEN_PREFIX}{slug}"

    def _builtin_logo_label_from_token(self, token: str) -> Optional[str]:
        norm = token.strip().lower()
        for label in self._builtin_logo_paths.keys():
            if norm == self._builtin_logo_token_for_label(label):
                return label
        return None

    def _project_root(self) -> Path:
        if getattr(sys, "frozen", False):
            base = getattr(sys, "_MEIPASS", None)
            if base:
                return Path(base)
        return Path(__file__).resolve().parents[1]

    def _set_application_icon(self) -> None:
        root = self._project_root()
        ico_path = root / "assets" / "app_icon.ico"
        png_candidates = [
            root / "assets" / "app_icon.png",
            root / "assets" / "logos" / "logo_phusis.png",
        ]

        if ico_path.exists():
            try:
                self.root.iconbitmap(default=str(ico_path))
                return
            except Exception:
                pass

        for png_path in png_candidates:
            if not png_path.exists():
                continue
            try:
                self._window_icon_photo = tk.PhotoImage(file=str(png_path))
                self.root.iconphoto(True, self._window_icon_photo)
                return
            except Exception:
                continue

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.root.grid_columnconfigure(
            0,
            weight=LEFT_PANEL_WEIGHT,
            minsize=LEFT_PANEL_MIN_WIDTH,
            uniform="layout",
        )
        self.root.grid_columnconfigure(
            1,
            weight=RIGHT_PANEL_WEIGHT,
            minsize=RIGHT_PANEL_MIN_WIDTH,
            uniform="layout",
        )
        self.root.grid_rowconfigure(0, weight=1)

        self.left_panel = ctk.CTkFrame(self.root, corner_radius=16)
        self.right_panel = ctk.CTkFrame(self.root, corner_radius=16)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(14, 8), pady=14)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 14), pady=14)

        self._build_left(self.left_panel)
        self._build_right(self.right_panel)

    def _build_left(self, parent: ctk.CTkFrame) -> None:
        parent.grid_rowconfigure(3, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            parent,
            text="QR Studio Pro",
            font=ctk.CTkFont(size=26, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))

        basics = ctk.CTkFrame(parent, corner_radius=12)
        basics.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))
        basics.grid_columnconfigure(1, weight=1)

        # --- URL ---
        url_label = ctk.CTkLabel(basics, text="URL", anchor="w")
        url_label.grid(row=0, column=0, sticky="w", padx=12, pady=7)
        url_entry = ctk.CTkEntry(basics, textvariable=self.url_var)
        url_entry.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(6, 12), pady=7)
        self.tooltips.append(ToolTip(url_label, "URL ou texte à encoder dans le QR code"))
        self.tooltips.append(ToolTip(url_entry, "URL ou texte à encoder dans le QR code"))

        # --- Preset ---
        preset_label = ctk.CTkLabel(basics, text="Preset", anchor="w")
        preset_label.grid(row=1, column=0, sticky="w", padx=12, pady=7)
        self.preset_menu = ctk.CTkOptionMenu(
            basics,
            variable=self.preset_var,
            values=self._all_preset_names(),
            command=self._on_preset_changed,
            width=220,
            dynamic_resizing=False,
        )
        self.preset_menu.grid(row=1, column=1, sticky="w", padx=(6, 6), pady=7)
        reload_btn = ctk.CTkButton(
            basics,
            text="Reload",
            width=88,
            command=self._reload_preset,
        )
        reload_btn.grid(row=1, column=2, sticky="e", padx=(2, 12), pady=7)
        self.tooltips.append(ToolTip(preset_label, "Thème graphique prédéfini à appliquer"))
        self.tooltips.append(ToolTip(self.preset_menu, "Thème graphique prédéfini à appliquer"))
        self.tooltips.append(ToolTip(reload_btn, "Réinitialise les paramètres graphiques au preset sélectionné"))

        self._add_preset_io_row(basics, row=2)
        self._add_logo_row(basics, row=3)
        self._add_output_row(basics, row=5)
        self._add_qr_technical_row(basics, row=6)
        self._add_export_row(basics, row=7)

        self.drop_zone = ctk.CTkLabel(
            basics,
            text="📂  Glissez-déposez un logo ici",
            corner_radius=8,
            fg_color=("#dbe4ef", "#28303a"),
            text_color=("#1f2937", "#d1d5db"),
            height=36,
        )
        self.drop_zone.grid(row=8, column=0, columnspan=3, sticky="ew", padx=12, pady=(4, 10))
        self.tooltips.append(ToolTip(self.drop_zone, "Glissez-déposez un fichier image ici pour l'utiliser comme logo"))

        actions = ctk.CTkFrame(parent, corner_radius=12)
        actions.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))

        sw_auto = ctk.CTkSwitch(actions, text="Auto Preview", variable=self.auto_preview_var)
        sw_auto.grid(row=0, column=0, sticky="w", padx=12, pady=10)
        self.tooltips.append(ToolTip(sw_auto, "Actualise l'aperçu automatiquement à chaque modification de paramètre"))

        sw_decode = ctk.CTkSwitch(actions, text="Decode Check", variable=self.decode_var)
        sw_decode.grid(row=0, column=1, sticky="w", padx=12, pady=10)
        self.tooltips.append(ToolTip(sw_decode, "Vérifie que le QR généré est lisible via OpenCV après export"))

        sw_quiet = ctk.CTkSwitch(actions, text="Quiet Logs", variable=self.quiet_var)
        sw_quiet.grid(row=0, column=2, sticky="w", padx=12, pady=10)
        self.tooltips.append(ToolTip(sw_quiet, "Désactive les logs de génération dans la console"))

        preview_btn = ctk.CTkButton(actions, text="👁  Preview", command=self._render_preview_manual)
        preview_btn.grid(row=0, column=3, sticky="e", padx=(8, 6), pady=10)
        self.tooltips.append(ToolTip(preview_btn, "Génère un aperçu sans sauvegarder de fichier"))

        self.export_btn = ctk.CTkButton(
            actions,
            text="💾  Export QR",
            command=self._save_qr,
            fg_color=("#166534", "#22c55e"),
            hover_color=("#15803d", "#16a34a"),
        )
        self.export_btn.grid(row=0, column=4, sticky="e", padx=(6, 12), pady=10)
        self.tooltips.append(ToolTip(self.export_btn, "Exporte le QR code dans le format et chemin sélectionnés"))

        for col in range(5):
            actions.grid_columnconfigure(col, weight=1)

        split_label = ctk.CTkLabel(actions, text="Preview Width", anchor="w")
        split_label.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 10))
        split_slider = ctk.CTkSlider(
            actions,
            from_=RIGHT_PANEL_RATIO_MIN,
            to=RIGHT_PANEL_RATIO_MAX,
            number_of_steps=34,
            variable=self.preview_split_ratio_var,
            command=self._on_split_ratio_changed,
        )
        split_slider.grid(row=1, column=1, columnspan=3, sticky="ew", padx=(0, 8), pady=(0, 10))
        split_value = ctk.CTkLabel(actions, textvariable=self.preview_split_text_var, width=52, anchor="e")
        split_value.grid(row=1, column=4, sticky="e", padx=(6, 12), pady=(0, 10))
        self.tooltips.append(ToolTip(split_label, "Ajuste la largeur relative de la zone Live Preview"))
        self.tooltips.append(ToolTip(split_slider, "Ajuste la largeur relative de la zone Live Preview"))

        config_card = ctk.CTkFrame(parent, corner_radius=12)
        config_card.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 12))
        config_card.grid_rowconfigure(1, weight=1)
        config_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            config_card,
            text="🎨  Graphic Parameters",
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 8))

        self.tabview = ctk.CTkTabview(config_card)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        tab_frames: Dict[str, ctk.CTkScrollableFrame] = {}
        tab_rows: Dict[str, int] = {}

        for group_name in GROUP_ORDER:
            self.tabview.add(group_name)
            tab = self.tabview.tab(group_name)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)

            scroll = ctk.CTkScrollableFrame(tab, corner_radius=8)
            scroll.grid(row=0, column=0, sticky="nsew", padx=4, pady=6)
            scroll.grid_columnconfigure(1, weight=1)
            tab_frames[group_name] = scroll
            if group_name == "Full Dark":
                self.full_dark_hint_label = ctk.CTkLabel(
                    scroll,
                    text="⚠  Actif uniquement en mode full_dark_artistic",
                    anchor="w",
                    text_color=("#64748b", "#94a3b8"),
                    font=ctk.CTkFont(size=12, slant="italic"),
                )
                self.full_dark_hint_label.grid(row=0, column=0, columnspan=3, sticky="ew", padx=4, pady=(2, 8))
                tab_rows[group_name] = 1
            else:
                tab_rows[group_name] = 0

        default_cfg = GraphicConfig()
        for field in fields(GraphicConfig):
            spec = get_field_spec(field.name)
            group_name = spec.group if spec else "General"
            if group_name not in tab_frames:
                group_name = "General"

            row = tab_rows[group_name]
            self._create_field_control(
                parent=tab_frames[group_name],
                row=row,
                field_name=field.name,
                default_value=getattr(default_cfg, field.name),
                description=spec.description if spec else field.name,
                label_text=spec.label if spec else field.name,
                group_name=group_name,
            )
            tab_rows[group_name] = row + 1

        self._setup_logo_drag_and_drop()
        self._update_full_dark_section_state()

    def _build_right(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            parent,
            text="🖼  Live Preview",
            font=ctk.CTkFont(size=22, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))

        preview_card = ctk.CTkFrame(parent, corner_radius=12)
        preview_card.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))
        preview_card.grid_columnconfigure(0, weight=1)
        preview_card.grid_rowconfigure(1, weight=1)

        self.preview_meta_label = ctk.CTkLabel(
            preview_card,
            text="Waiting for first render...",
            anchor="w",
            text_color=("#2e3a4f", "#9ca7bf"),
        )
        self.preview_meta_label.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))

        self.preview_image_label = ctk.CTkLabel(
            preview_card,
            text="",
            fg_color=("#f7fafc", "#10151d"),
            corner_radius=10,
        )
        self.preview_image_label.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self.status_label = ctk.CTkLabel(
            parent,
            text="Ready",
            anchor="w",
            corner_radius=8,
            fg_color=("#edf2ff", "#1c2432"),
            text_color=("#213153", "#c7d2fe"),
        )
        self.status_label.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12), ipady=8)

    def _add_labeled_entry(
        self, parent: ctk.CTkFrame, label: str, variable: tk.StringVar, row: int, tooltip: str = "",
    ) -> None:
        lbl = ctk.CTkLabel(parent, text=label, anchor="w")
        lbl.grid(row=row, column=0, sticky="w", padx=12, pady=7)
        entry = ctk.CTkEntry(parent, textvariable=variable)
        entry.grid(row=row, column=1, columnspan=2, sticky="ew", padx=(6, 12), pady=7)
        if tooltip:
            self.tooltips.append(ToolTip(lbl, tooltip))
            self.tooltips.append(ToolTip(entry, tooltip))

    def _add_logo_row(self, parent: ctk.CTkFrame, row: int) -> None:
        logo_label = ctk.CTkLabel(parent, text="Logo", anchor="w")
        logo_label.grid(row=row, column=0, sticky="w", padx=12, pady=7)
        self.logo_entry = ctk.CTkEntry(parent, textvariable=self.logo_var)
        self.logo_entry.grid(row=row, column=1, sticky="ew", padx=(6, 6), pady=7)

        button_wrap = ctk.CTkFrame(parent, fg_color="transparent")
        button_wrap.grid(row=row, column=2, sticky="e", padx=(2, 12), pady=7)
        browse_btn = ctk.CTkButton(button_wrap, text="Browse", width=74, command=self._pick_logo)
        browse_btn.grid(row=0, column=0, padx=(0, 6))
        clear_btn = ctk.CTkButton(button_wrap, text="Clear", width=58, command=lambda: self.logo_var.set(""))
        clear_btn.grid(row=0, column=1)

        self.tooltips.append(ToolTip(logo_label, "Chemin vers le fichier logo (PNG, JPG, WEBP…)"))
        self.tooltips.append(ToolTip(self.logo_entry, "Chemin vers le fichier logo (PNG, JPG, WEBP…)"))
        self.tooltips.append(ToolTip(browse_btn, "Parcourir pour sélectionner un fichier logo"))
        self.tooltips.append(ToolTip(clear_btn, "Retirer le logo du QR code"))

        lib_label = ctk.CTkLabel(parent, text="Built-in", anchor="w")
        lib_label.grid(row=row + 1, column=0, sticky="w", padx=12, pady=(0, 7))
        self.logo_library_menu = ctk.CTkOptionMenu(
            parent,
            variable=self.logo_library_var,
            values=self._logo_library_values(),
            command=self._on_logo_library_changed,
            width=220,
            dynamic_resizing=False,
        )
        self.logo_library_menu.grid(row=row + 1, column=1, sticky="w", padx=(6, 6), pady=(0, 7))
        self.tooltips.append(ToolTip(lib_label, "Sélectionne un logo intégré à l'application"))
        self.tooltips.append(ToolTip(self.logo_library_menu, "Phusis / Romane Pena / sans logo / custom"))

    def _add_output_row(self, parent: ctk.CTkFrame, row: int) -> None:
        output_label = ctk.CTkLabel(parent, text="Output", anchor="w")
        output_label.grid(row=row, column=0, sticky="w", padx=12, pady=7)
        self.output_entry = ctk.CTkEntry(parent, textvariable=self.output_var)
        self.output_entry.grid(row=row, column=1, sticky="ew", padx=(6, 6), pady=7)

        choose_btn = ctk.CTkButton(parent, text="Choose", width=138, command=self._pick_output)
        choose_btn.grid(row=row, column=2, sticky="e", padx=(2, 12), pady=7)

        self.tooltips.append(ToolTip(output_label, "Chemin de sortie du fichier QR généré"))
        self.tooltips.append(ToolTip(self.output_entry, "Chemin de sortie du fichier QR généré"))
        self.tooltips.append(ToolTip(choose_btn, "Choisir l'emplacement de sauvegarde"))

    def _add_preset_io_row(self, parent: ctk.CTkFrame, row: int) -> None:
        io_label = ctk.CTkLabel(parent, text="Preset IO", anchor="w")
        io_label.grid(row=row, column=0, sticky="w", padx=12, pady=7)

        button_row = ctk.CTkFrame(parent, fg_color="transparent")
        button_row.grid(row=row, column=1, columnspan=2, sticky="ew", padx=(6, 12), pady=7)
        button_row.grid_columnconfigure(0, weight=1)
        button_row.grid_columnconfigure(1, weight=1)

        import_btn = ctk.CTkButton(
            button_row,
            text="Import JSON",
            command=self._import_preset_from_file,
        )
        import_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        save_btn = ctk.CTkButton(
            button_row,
            text="Save Preset",
            command=self._save_current_as_preset,
        )
        save_btn.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        self.tooltips.append(ToolTip(io_label, "Importer un preset JSON ou sauvegarder la config courante"))
        self.tooltips.append(ToolTip(import_btn, "Importe un preset JSON puis l'ajoute à la liste des presets"))
        self.tooltips.append(ToolTip(save_btn, "Sauvegarde les paramètres courants en preset JSON"))

    def _add_qr_technical_row(self, parent: ctk.CTkFrame, row: int) -> None:
        tech_label = ctk.CTkLabel(parent, text="QR Tech", anchor="w")
        tech_label.grid(row=row, column=0, sticky="w", padx=12, pady=7)
        self.tooltips.append(ToolTip(tech_label, "Paramètres techniques de génération du QR code"))

        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.grid(row=row, column=1, columnspan=2, sticky="ew", padx=(6, 12), pady=7)
        wrap.grid_columnconfigure(1, weight=1)
        wrap.grid_columnconfigure(3, weight=1)

        box_label = ctk.CTkLabel(wrap, text="Box")
        box_label.grid(row=0, column=0, sticky="w")
        box_entry = ctk.CTkEntry(wrap, textvariable=self.box_size_var, width=72)
        box_entry.grid(row=0, column=1, sticky="w", padx=(6, 14))
        self.tooltips.append(ToolTip(box_label, "Taille en pixels de chaque module du QR (plus grand = image plus haute résolution)"))
        self.tooltips.append(ToolTip(box_entry, "Taille en pixels de chaque module du QR (plus grand = image plus haute résolution)"))

        border_label = ctk.CTkLabel(wrap, text="Border")
        border_label.grid(row=0, column=2, sticky="w")
        border_entry = ctk.CTkEntry(wrap, textvariable=self.border_var, width=72)
        border_entry.grid(row=0, column=3, sticky="w", padx=(6, 0))
        self.tooltips.append(ToolTip(border_label, "Nombre de modules de marge autour du QR (min. recommandé : 4)"))
        self.tooltips.append(ToolTip(border_entry, "Nombre de modules de marge autour du QR (min. recommandé : 4)"))

    def _add_export_row(self, parent: ctk.CTkFrame, row: int) -> None:
        export_label = ctk.CTkLabel(parent, text="Export", anchor="w")
        export_label.grid(row=row, column=0, sticky="w", padx=12, pady=7)
        self.tooltips.append(ToolTip(export_label, "Paramètres d'export du fichier image"))

        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.grid(row=row, column=1, columnspan=2, sticky="ew", padx=(6, 12), pady=7)
        wrap.grid_columnconfigure(5, weight=1)

        fmt_label = ctk.CTkLabel(wrap, text="Format")
        fmt_label.grid(row=0, column=0, sticky="w")
        fmt_menu = ctk.CTkOptionMenu(
            wrap,
            variable=self.output_format_var,
            values=["auto", "png", "webp", "jpeg", "svg"],
            width=90,
            dynamic_resizing=False,
            command=self._on_format_changed,
        )
        fmt_menu.grid(row=0, column=1, sticky="w", padx=(6, 12))
        self.tooltips.append(ToolTip(fmt_label, "Format d'export : 'auto' détecte depuis l'extension du fichier"))
        self.tooltips.append(ToolTip(fmt_menu, "Format d'export : 'auto' détecte depuis l'extension du fichier"))

        quality_label = ctk.CTkLabel(wrap, text="Quality")
        quality_label.grid(row=0, column=2, sticky="w")
        quality_slider = ctk.CTkSlider(
            wrap,
            from_=1,
            to=100,
            number_of_steps=99,
            variable=self.output_quality_var,
            width=110,
        )
        quality_slider.grid(row=0, column=3, sticky="w", padx=(6, 12))
        quality_val_label = ctk.CTkLabel(wrap, textvariable=self.output_quality_var, width=30)
        quality_val_label.grid(row=0, column=4, sticky="w")
        self.tooltips.append(ToolTip(quality_label, "Qualité de compression (JPEG/WEBP uniquement, 1-100)"))
        self.tooltips.append(ToolTip(quality_slider, "Qualité de compression (JPEG/WEBP uniquement, 1-100)"))
        self._export_quality_widgets = [quality_label, quality_slider, quality_val_label]

        maxw_label = ctk.CTkLabel(wrap, text="MaxW")
        maxw_label.grid(row=0, column=5, sticky="e")
        maxw_entry = ctk.CTkEntry(wrap, textvariable=self.output_max_width_var, width=84)
        maxw_entry.grid(row=0, column=6, sticky="e", padx=(6, 0))
        self.tooltips.append(ToolTip(maxw_label, "Largeur max en pixels de l'image exportée (vide = taille originale)"))
        self.tooltips.append(ToolTip(maxw_entry, "Largeur max en pixels de l'image exportée (vide = taille originale)"))
        self._export_maxw_widgets = [maxw_label, maxw_entry]

    def _create_field_control(
        self,
        parent: ctk.CTkScrollableFrame,
        row: int,
        field_name: str,
        default_value: Any,
        description: str,
        label_text: str,
        group_name: str,
    ) -> None:
        label_wrap = ctk.CTkFrame(parent, fg_color="transparent")
        label_wrap.grid(row=row, column=0, sticky="w", padx=(4, 8), pady=5)

        label = ctk.CTkLabel(label_wrap, text=label_text, anchor="w")
        label.grid(row=0, column=0, sticky="w")
        info = ctk.CTkLabel(label_wrap, text=" ⓘ", text_color=("#64748b", "#94a3b8"))
        info.grid(row=0, column=1, sticky="w")

        self.tooltips.append(ToolTip(label, description))
        self.tooltips.append(ToolTip(info, description))

        # Track labels for Full Dark graying
        self.group_input_widgets[group_name].append(label_wrap)

        if field_name == "style_mode":
            var = tk.StringVar(value=str(default_value))
            control = ctk.CTkOptionMenu(
                parent,
                variable=var,
                values=STYLE_MODE_VALUES,
                width=210,
                dynamic_resizing=False,
                command=lambda _v: self._on_style_mode_changed(),
            )
            control.grid(row=row, column=1, sticky="w", pady=5)
            self.graphic_vars[field_name] = var
            self.group_input_widgets[group_name].append(control)
            return

        if field_name == "module_shape":
            var = tk.StringVar(value=str(default_value))
            control = ctk.CTkOptionMenu(
                parent,
                variable=var,
                values=["square", "rounded", "dot"],
                width=210,
                dynamic_resizing=False,
                command=lambda _v: self._schedule_auto_preview(),
            )
            control.grid(row=row, column=1, sticky="w", pady=5)
            self.graphic_vars[field_name] = var
            self.group_input_widgets[group_name].append(control)
            return

        if field_name in {"module_scale", "module_corner_ratio"}:
            slider_min = 0.45 if field_name == "module_scale" else 0.0
            slider_max = 1.20 if field_name == "module_scale" else 1.0
            steps = 75 if field_name == "module_scale" else 100
            var = tk.DoubleVar(value=float(default_value))
            value_text = tk.StringVar(value=f"{float(default_value):.2f}")

            def _sync_slider_label(*_args):
                value_text.set(f"{float(var.get()):.2f}")

            def _on_slider(_value: float):
                _sync_slider_label()
                self._schedule_auto_preview()

            var.trace_add("write", _sync_slider_label)

            control_wrap = ctk.CTkFrame(parent, fg_color="transparent")
            control_wrap.grid(row=row, column=1, sticky="ew", pady=5)
            control_wrap.grid_columnconfigure(0, weight=1)

            slider = ctk.CTkSlider(
                control_wrap,
                from_=slider_min,
                to=slider_max,
                number_of_steps=steps,
                variable=var,
                command=_on_slider,
            )
            slider.grid(row=0, column=0, sticky="ew", padx=(0, 10))

            value_label = ctk.CTkLabel(control_wrap, textvariable=value_text, width=42, anchor="e")
            value_label.grid(row=0, column=1, sticky="e")

            self.graphic_vars[field_name] = var
            self.group_input_widgets[group_name].append(control_wrap)
            return

        if isinstance(default_value, bool):
            var = tk.BooleanVar(value=default_value)
            control = ctk.CTkSwitch(
                parent,
                text="",
                variable=var,
                command=self._schedule_auto_preview,
            )
            control.grid(row=row, column=1, sticky="w", pady=5)
            self.graphic_vars[field_name] = var
            self.group_input_widgets[group_name].append(control)
            return

        var = tk.StringVar(value=self._serialize_value(field_name, default_value))
        entry = ctk.CTkEntry(parent, textvariable=var)
        entry.grid(row=row, column=1, sticky="ew", pady=5)
        self.graphic_vars[field_name] = var
        self.group_input_widgets[group_name].append(entry)

        if self._is_color_field(default_value, field_name):
            btn_swatch_wrap = ctk.CTkFrame(parent, fg_color="transparent")
            btn_swatch_wrap.grid(row=row, column=2, sticky="w", padx=(8, 4), pady=5)

            swatch = ctk.CTkFrame(btn_swatch_wrap, width=18, height=18, corner_radius=4)
            swatch.grid(row=0, column=0, padx=(0, 6))
            swatch.configure(fg_color=self._tuple_to_hex(default_value))
            self.color_swatches[field_name] = swatch

            color_btn = ctk.CTkButton(
                btn_swatch_wrap,
                text="Palette",
                width=72,
                command=lambda n=field_name: self._choose_color(n),
            )
            color_btn.grid(row=0, column=1)
            self.group_input_widgets[group_name].append(btn_swatch_wrap)

    # ------------------------------------------------------------------
    # Drag and drop logo
    # ------------------------------------------------------------------

    def _setup_logo_drag_and_drop(self) -> None:
        if DND_FILES is None:
            self.drop_zone.configure(text="Drag and drop unavailable (install tkinterdnd2)")
            return

        targets = [self.drop_zone, self.logo_entry]
        enabled = False
        for widget in targets:
            if not hasattr(widget, "drop_target_register") or not hasattr(widget, "dnd_bind"):
                continue
            try:
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", self._on_logo_drop)
                enabled = True
            except Exception:
                continue

        if not enabled:
            self.drop_zone.configure(text="Drag and drop unavailable in current runtime")

    def _on_logo_drop(self, event: tk.Event) -> None:
        try:
            dropped = self.root.tk.splitlist(event.data)
        except Exception:
            dropped = [event.data]

        if not dropped:
            return

        path = str(dropped[0]).strip()
        if path.startswith("{") and path.endswith("}"):
            path = path[1:-1]

        self.logo_var.set(path)
        self._set_status(f"Logo loaded: {path}")
        self._schedule_auto_preview()

    def _on_logo_library_changed(self, choice: str) -> None:
        if choice == "Custom":
            return

        selected = self._builtin_logo_paths.get(choice)
        self._logo_library_sync_lock = True
        try:
            if selected is None:
                self.logo_var.set("none")
                self._set_status("Logo intégré: aucun logo")
            else:
                self.logo_var.set(self._builtin_logo_token_for_label(choice))
                self._set_status(f"Logo intégré: {choice}")
        finally:
            self._logo_library_sync_lock = False
        self._apply_logo_recommended_preset(choice, show_status=True)
        self._schedule_auto_preview()

    def _apply_logo_recommended_preset(self, choice: str, show_status: bool = True) -> None:
        recommended_map = {
            "Phusis": "full_dark_artistic",
            "Romane Pena": "pena_psychologue",
        }
        preset_name = recommended_map.get(choice)
        if not preset_name:
            return
        if preset_name not in self._all_preset_names():
            return
        if self.preset_var.get().strip() == preset_name:
            return

        self.preset_var.set(preset_name)
        self._load_preset(preset_name)
        if show_status:
            self._set_status(f"Preset auto: {preset_name} (logo {choice})")

    def _sync_logo_library_selection(self) -> None:
        if self._logo_library_sync_lock:
            return

        raw = self.logo_var.get().strip()
        lowered = raw.lower()
        target_choice = "Custom"

        if lowered in {"", "none", "null", "sans"}:
            target_choice = "No logo"
        elif lowered.startswith(BUILTIN_LOGO_TOKEN_PREFIX):
            label = self._builtin_logo_label_from_token(lowered)
            if label is not None:
                target_choice = label
        else:
            raw_path = Path(raw)
            try:
                resolved_raw = raw_path.resolve(strict=False)
            except Exception:
                resolved_raw = raw_path

            for label, path in self._builtin_logo_paths.items():
                if path is None:
                    continue
                try:
                    if resolved_raw == path.resolve(strict=False):
                        target_choice = label
                        break
                except Exception:
                    if str(raw_path) == str(path):
                        target_choice = label
                        break

        if self.logo_library_var.get() != target_choice:
            self._logo_library_sync_lock = True
            try:
                self.logo_library_var.set(target_choice)
            finally:
                self._logo_library_sync_lock = False

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _is_color_field(self, value: Any, field_name: str) -> bool:
        if not isinstance(value, tuple):
            return False
        if len(value) not in (3, 4):
            return False
        return field_name.endswith("_rgb") or field_name.endswith("_rgba") or "color" in field_name

    def _serialize_value(self, field_name: str, value: Any) -> str:
        if value is None and field_name in OPTIONAL_TUPLE_FIELDS:
            return "none"
        if isinstance(value, tuple):
            return ",".join(str(v) for v in value)
        return str(value)

    def _parse_tuple(
        self,
        raw: str,
        expected_len: int,
        allow_none: bool,
        clamp_as_color: bool,
    ) -> Optional[tuple[int, ...]]:
        text = raw.strip()
        if allow_none and text.lower() in {"", "none", "null"}:
            return None

        parts = [p.strip() for p in text.split(",") if p.strip()]
        if len(parts) != expected_len:
            raise ValueError(f"{expected_len} values expected, got: {raw}")

        vals: list[int] = []
        for p in parts:
            v = int(p)
            if clamp_as_color and (v < 0 or v > 255):
                raise ValueError("Color values must be in [0,255]")
            vals.append(v)

        return tuple(vals)

    def _collect_graphic_overrides(self) -> Dict[str, Any]:
        base = GraphicConfig()
        overrides: Dict[str, Any] = {}

        for field in fields(GraphicConfig):
            default_value = getattr(base, field.name)
            var = self.graphic_vars[field.name]

            if isinstance(var, tk.BooleanVar):
                overrides[field.name] = bool(var.get())
                continue

            raw = str(var.get()).strip()
            if isinstance(default_value, tuple):
                overrides[field.name] = self._parse_tuple(
                    raw,
                    expected_len=len(default_value),
                    allow_none=field.name in OPTIONAL_TUPLE_FIELDS,
                    clamp_as_color=self._is_color_field(default_value, field.name),
                )
            elif isinstance(default_value, int):
                overrides[field.name] = int(raw)
            elif isinstance(default_value, float):
                overrides[field.name] = float(raw)
            else:
                overrides[field.name] = raw

        return overrides

    def _resolve_logo_path(self) -> Optional[Path]:
        raw = self.logo_var.get().strip()
        lowered = raw.lower()
        if lowered in {"", "none", "null", "sans"}:
            return None
        if lowered.startswith(BUILTIN_LOGO_TOKEN_PREFIX):
            label = self._builtin_logo_label_from_token(lowered)
            if label is None:
                raise ValueError(f"Builtin logo inconnu: {raw}")
            resolved = self._builtin_logo_paths.get(label)
            if resolved is None:
                return None
            return resolved
        return Path(raw)

    def _parse_positive_int(self, raw: str, field_name: str) -> int:
        value = int(raw.strip())
        if value <= 0:
            raise ValueError(f"{field_name} must be > 0")
        return value

    def _parse_optional_positive_int(self, raw: str, field_name: str) -> Optional[int]:
        text = raw.strip()
        if not text:
            return None
        return self._parse_positive_int(text, field_name)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _build_runtime_config(self):
        url = self.url_var.get().strip()
        if not url:
            raise ValueError("URL is required")

        output = self.output_var.get().strip()
        if not output:
            raise ValueError("Output path is required")

        box_size = self._parse_positive_int(self.box_size_var.get(), "box_size")
        border = self._parse_positive_int(self.border_var.get(), "border")
        selected_preset = self.preset_var.get().strip()
        base_preset = selected_preset if selected_preset in self._builtin_preset_names else None

        return create_qr_config(
            url=url,
            preset_name=base_preset,
            logo_path=self._resolve_logo_path(),
            output_path=Path(output),
            box_size=box_size,
            border=border,
            graphic_overrides=self._collect_graphic_overrides(),
            run_decode_check=self.decode_var.get(),
            verbose=not self.quiet_var.get(),
        )

    def _pick_logo(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select logo",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.gif *.svg"), ("All", "*.*")],
        )
        if selected:
            self.logo_var.set(selected)
            self._schedule_auto_preview()

    def _pick_output(self) -> None:
        selected = filedialog.asksaveasfilename(
            title="Select output path",
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("All", "*.*")],
            initialfile=Path(self.output_var.get() or "generated_qrcode/qr_output.png").name,
        )
        if selected:
            self.output_var.set(selected)

    def _choose_color(self, field_name: str) -> None:
        var = self.graphic_vars.get(field_name)
        if not isinstance(var, tk.StringVar):
            return

        current = var.get().strip()
        if current.lower() in {"", "none", "null"}:
            base_rgb = (128, 128, 128)
            alpha = 255
            component_count = 3
        else:
            component_count = 4 if current.count(",") == 3 else 3
            parsed = self._parse_tuple(
                current,
                expected_len=component_count,
                allow_none=False,
                clamp_as_color=True,
            )
            if parsed is None:
                return
            base_rgb = parsed[:3]
            alpha = parsed[3] if len(parsed) == 4 else 255

        chosen = colorchooser.askcolor(
            color="#%02x%02x%02x" % base_rgb,
            title=f"Choose {field_name}",
        )
        if not chosen or chosen[0] is None:
            return

        rgb = tuple(int(v) for v in chosen[0])
        if component_count == 4:
            var.set(f"{rgb[0]},{rgb[1]},{rgb[2]},{alpha}")
        else:
            var.set(f"{rgb[0]},{rgb[1]},{rgb[2]}")

        self._update_color_swatch(field_name)
        self._schedule_auto_preview()

    # ------------------------------------------------------------------
    # Helpers: color swatches & format
    # ------------------------------------------------------------------

    @staticmethod
    def _tuple_to_hex(value) -> str:
        """Convert a color tuple (R, G, B) or (R, G, B, A) to a hex string."""
        if isinstance(value, tuple) and len(value) >= 3:
            return "#%02x%02x%02x" % value[:3]
        return "#808080"

    def _update_color_swatch(self, field_name: str) -> None:
        swatch = self.color_swatches.get(field_name)
        if swatch is None:
            return
        var = self.graphic_vars.get(field_name)
        if not isinstance(var, tk.StringVar):
            return
        raw = var.get().strip()
        if raw.lower() in {"", "none", "null"}:
            swatch.configure(fg_color="#808080")
            return
        try:
            parts = [int(p.strip()) for p in raw.split(",") if p.strip()]
            if len(parts) >= 3:
                swatch.configure(fg_color="#%02x%02x%02x" % tuple(parts[:3]))
        except (ValueError, TypeError):
            pass

    def _update_all_color_swatches(self) -> None:
        for field_name in self.color_swatches:
            self._update_color_swatch(field_name)

    def _on_format_changed(self, choice: str) -> None:
        fmt = choice.strip().lower()
        # Auto-update the output extension
        ext_map = {"png": ".png", "webp": ".webp", "jpeg": ".jpg", "svg": ".svg"}
        if fmt in ext_map:
            current = self.output_var.get().strip()
            if current:
                p = Path(current)
                self.output_var.set(str(p.with_suffix(ext_map[fmt])))

        # Disable Quality slider for SVG and PNG (lossless)
        quality_state = "disabled" if fmt in {"svg", "png"} else "normal"
        for w in self._export_quality_widgets:
            try:
                w.configure(state=quality_state)
            except Exception:
                pass

        # Disable MaxW for SVG (vectorial)
        maxw_state = "disabled" if fmt == "svg" else "normal"
        for w in self._export_maxw_widgets:
            try:
                w.configure(state=maxw_state)
            except Exception:
                pass

    def _on_split_ratio_changed(self, value: float) -> None:
        ratio = max(RIGHT_PANEL_RATIO_MIN, min(RIGHT_PANEL_RATIO_MAX, float(value)))
        if abs(ratio - float(self.preview_split_ratio_var.get())) > 1e-6:
            self.preview_split_ratio_var.set(ratio)
        self._apply_layout_split_ratio(ratio)

    def _apply_layout_split_ratio(self, right_ratio: float) -> None:
        ratio = max(RIGHT_PANEL_RATIO_MIN, min(RIGHT_PANEL_RATIO_MAX, float(right_ratio)))
        left_ratio = 1.0 - ratio
        left_weight = max(1, int(round(left_ratio * 100)))
        right_weight = max(1, int(round(ratio * 100)))

        self.root.grid_columnconfigure(
            0,
            weight=left_weight,
            minsize=LEFT_PANEL_MIN_WIDTH,
            uniform="layout",
        )
        self.root.grid_columnconfigure(
            1,
            weight=right_weight,
            minsize=RIGHT_PANEL_MIN_WIDTH,
            uniform="layout",
        )
        self.preview_split_text_var.set(f"{int(round(ratio * 100))}%")

        if not self._layout_lock_active:
            self._schedule_preview_resize()

    def _render_preview(self, show_errors: bool) -> None:
        try:
            cfg = self._build_runtime_config()
            image = BrandedQRGenerator(cfg).render()
        except Exception as exc:
            self._set_status(f"Preview not updated: {exc}", is_error=True)
            if show_errors:
                messagebox.showerror("Preview error", str(exc))
            return

        self._last_rendered_image = image.copy()
        self._preview_source_image = image.copy()
        self._set_preview_image(self._preview_source_image, recreate_ctk_image=True)
        self.preview_meta_label.configure(text=f"Preset: {cfg.graphic.style_mode} | Canvas: {image.width}x{image.height}")
        self._set_status("Preview updated")

    def _compute_preview_size(self, image: Image.Image) -> tuple[int, int]:
        avail_w = max(280, self.preview_image_label.winfo_width() - 24)
        avail_h = max(280, self.preview_image_label.winfo_height() - 24)
        src_w, src_h = image.size
        ratio = min(avail_w / max(1, src_w), avail_h / max(1, src_h), 1.0)
        return max(1, int(src_w * ratio)), max(1, int(src_h * ratio))

    def _set_preview_image(self, image: Image.Image, recreate_ctk_image: bool) -> None:
        target_size = self._compute_preview_size(image)
        self._last_preview_render_size = target_size

        if recreate_ctk_image or self._preview_ctk_image is None:
            self._preview_ctk_image = ctk.CTkImage(
                light_image=image,
                dark_image=image,
                size=target_size,
            )
            self.preview_image_label.configure(image=self._preview_ctk_image, text="")
            return

        self._preview_ctk_image.configure(size=target_size)

    def _render_preview_manual(self) -> None:
        self._render_preview(show_errors=True)

    def _render_preview_silent(self) -> None:
        self._preview_job_id = None
        self._render_preview(show_errors=False)

    def _resolve_export_target(self, base_output: Path) -> tuple[Path, Optional[str]]:
        fmt = self.output_format_var.get().strip().lower()
        format_map: Dict[str, tuple[str, str]] = {
            "png": ("PNG", ".png"),
            "webp": ("WEBP", ".webp"),
            "jpeg": ("JPEG", ".jpg"),
            "svg": ("SVG", ".svg"),
            "auto": ("", ""),
        }
        if fmt not in format_map:
            raise ValueError(f"Unsupported output format: {fmt}")

        target_format, ext = format_map[fmt]
        if fmt == "auto":
            if not base_output.suffix:
                return base_output.with_suffix(".png"), None
            return base_output, None

        return base_output.with_suffix(ext), target_format

    def _save_qr(self) -> None:
        try:
            cfg = self._build_runtime_config()
            max_width = self._parse_optional_positive_int(self.output_max_width_var.get(), "max_width")
            target_output, target_format = self._resolve_export_target(cfg.output_path)
            quality = int(self.output_quality_var.get())

            gen = BrandedQRGenerator(cfg)

            if target_format == "SVG":
                gen.save_svg(target_output)
            else:
                gen.save(
                    output_path=target_output,
                    image_format=target_format,
                    max_width=max_width,
                    quality=quality,
                )
            cfg.output_path = target_output
            self.output_var.set(str(target_output))
        except Exception as exc:
            self._set_status(f"Export failed: {exc}", is_error=True)
            messagebox.showerror("Export error", str(exc))
            return

        self._set_status(f"✅  Exported: {cfg.output_path}")
        if target_format != "SVG":
            self._render_preview(show_errors=False)
        messagebox.showinfo("Success", f"QR exported:\n{cfg.output_path}")

    # ------------------------------------------------------------------
    # Presets + auto preview
    # ------------------------------------------------------------------

    def _all_preset_names(self) -> list[str]:
        return self._builtin_preset_names + sorted(self._custom_presets.keys())

    @staticmethod
    def _normalize_preset_name(raw_name: str) -> str:
        cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in raw_name.strip())
        cleaned = cleaned.strip("_")
        return cleaned or "custom_preset"

    def _make_unique_preset_name(self, base_name: str) -> str:
        candidate = base_name
        existing = set(self._all_preset_names())
        if candidate not in existing:
            return candidate

        idx = 2
        while f"{candidate}_{idx}" in existing:
            idx += 1
        return f"{candidate}_{idx}"

    def _refresh_preset_menu(self, select_name: Optional[str] = None) -> None:
        values = self._all_preset_names()
        self.preset_menu.configure(values=values)
        if not values:
            return

        current = self.preset_var.get().strip()
        target = select_name if select_name in values else current
        if target not in values:
            target = values[0]
        self.preset_var.set(target)

    def _resolve_preset_config(self, preset_name: str) -> GraphicConfig:
        if preset_name in self._custom_presets:
            cfg = GraphicConfig()
            return apply_graphic_overrides(cfg, copy.deepcopy(self._custom_presets[preset_name]))
        return get_preset_graphic_config(preset_name)

    def _import_preset_from_file(self) -> None:
        selected = filedialog.askopenfilename(
            title="Importer un preset JSON",
            filetypes=[("Preset JSON", "*.json"), ("JSON", "*.json"), ("All", "*.*")],
        )
        if not selected:
            return

        try:
            imported_name, overrides = load_graphic_preset(Path(selected))
            # Validate before storing
            apply_graphic_overrides(GraphicConfig(), copy.deepcopy(overrides))
        except Exception as exc:
            self._set_status(f"Import preset failed: {exc}", is_error=True)
            messagebox.showerror("Import preset", str(exc))
            return

        base_name = imported_name or Path(selected).stem
        preset_name = self._make_unique_preset_name(self._normalize_preset_name(base_name))
        self._custom_presets[preset_name] = copy.deepcopy(overrides)
        self._refresh_preset_menu(select_name=preset_name)
        self._load_preset(preset_name)
        self._set_status(f"Preset imported: {preset_name}")

    def _save_current_as_preset(self) -> None:
        try:
            overrides = self._collect_graphic_overrides()
        except Exception as exc:
            self._set_status(f"Preset save failed: {exc}", is_error=True)
            messagebox.showerror("Save preset", str(exc))
            return

        suggested_name = self._normalize_preset_name(self.preset_var.get() or "custom_preset")
        raw_name = simpledialog.askstring(
            "Save preset",
            "Nom du preset:",
            initialvalue=suggested_name,
            parent=self.root,
        )
        if raw_name is None:
            return

        preset_name = self._make_unique_preset_name(self._normalize_preset_name(raw_name))
        default_dir = Path("qr_custom_presets")
        default_file = f"{preset_name}.json"
        selected = filedialog.asksaveasfilename(
            title="Sauvegarder le preset JSON",
            initialdir=str(default_dir),
            initialfile=default_file,
            defaultextension=".json",
            filetypes=[("Preset JSON", "*.json"), ("JSON", "*.json"), ("All", "*.*")],
        )
        if not selected:
            return

        selected_preset = self.preset_var.get().strip()
        base_preset = selected_preset if selected_preset in self._builtin_preset_names else None
        try:
            save_graphic_preset(
                path=Path(selected),
                preset_name=preset_name,
                graphic_overrides=overrides,
                base_preset=base_preset,
            )
        except Exception as exc:
            self._set_status(f"Preset save failed: {exc}", is_error=True)
            messagebox.showerror("Save preset", str(exc))
            return

        self._custom_presets[preset_name] = copy.deepcopy(overrides)
        self._refresh_preset_menu(select_name=preset_name)
        self._set_status(f"Preset saved: {preset_name}")

    def _on_preset_changed(self, _choice: str) -> None:
        self._load_preset(self.preset_var.get())
        self._set_status(f"Preset loaded: {self.preset_var.get()}")
        self._update_full_dark_section_state()

    def _reload_preset(self) -> None:
        self._load_preset(self.preset_var.get())
        self._set_status(f"Preset reloaded: {self.preset_var.get()}")
        self._update_full_dark_section_state()

    def _on_style_mode_changed(self) -> None:
        self._update_full_dark_section_state()
        self._schedule_auto_preview()

    def _update_full_dark_section_state(self) -> None:
        style_var = self.graphic_vars.get("style_mode")
        mode = str(style_var.get()) if isinstance(style_var, tk.StringVar) else ""
        enabled = mode == "full_dark_artistic"

        desired_state = "normal" if enabled else "disabled"
        disabled_text = ("#b0b0b0", "#4a4a4a")
        normal_text = ("#1f2937", "#d1d5db")
        for widget in self.group_input_widgets.get("Full Dark", []):
            try:
                widget.configure(state=desired_state)
            except Exception:
                pass
            # Grey out label text for visual feedback
            try:
                if isinstance(widget, (ctk.CTkLabel, ctk.CTkFrame)):
                    for child in widget.winfo_children():
                        if isinstance(child, ctk.CTkLabel):
                            child.configure(text_color=normal_text if enabled else disabled_text)
            except Exception:
                pass

        if self.full_dark_hint_label is not None:
            if enabled:
                self.full_dark_hint_label.configure(
                    text="✅  Paramètres Full Dark actifs",
                    text_color=("#166534", "#86efac"),
                )
            else:
                self.full_dark_hint_label.configure(
                    text="⚠  Actif uniquement en mode full_dark_artistic",
                    text_color=("#64748b", "#94a3b8"),
                )

    def _load_preset(self, preset_name: str) -> None:
        preset_cfg = self._resolve_preset_config(preset_name)

        self._suspend_auto_preview = True
        try:
            for field in fields(GraphicConfig):
                var = self.graphic_vars.get(field.name)
                if var is None:
                    continue
                value = getattr(preset_cfg, field.name)
                if isinstance(var, tk.BooleanVar):
                    var.set(bool(value))
                elif isinstance(var, tk.DoubleVar):
                    var.set(float(value))
                elif isinstance(var, tk.IntVar):
                    var.set(int(value))
                else:
                    var.set(self._serialize_value(field.name, value))
        finally:
            self._suspend_auto_preview = False

        self._update_full_dark_section_state()
        self._update_all_color_swatches()
        self._schedule_auto_preview()

    def _register_var_watchers(self) -> None:
        tracked = [
            self.url_var,
            self.logo_var,
            self.box_size_var,
            self.border_var,
            self.auto_preview_var,
        ]
        tracked.extend(self.graphic_vars.values())

        for var in tracked:
            var.trace_add("write", self._on_any_var_changed)
        self.logo_var.trace_add("write", self._on_logo_var_changed)

    def _on_logo_var_changed(self, *_args) -> None:
        self._sync_logo_library_selection()

    def _on_any_var_changed(self, *_args) -> None:
        if self._suspend_auto_preview:
            return
        self._schedule_auto_preview()

    def _schedule_auto_preview(self) -> None:
        if not self.auto_preview_var.get():
            if self._preview_job_id is not None:
                self.root.after_cancel(self._preview_job_id)
                self._preview_job_id = None
            return

        if self._preview_job_id is not None:
            self.root.after_cancel(self._preview_job_id)

        self._preview_job_id = self.root.after(280, self._render_preview_silent)

    def _on_root_configure(self, _event=None) -> None:
        current_size = (self.root.winfo_width(), self.root.winfo_height())
        if current_size == self._last_root_size:
            return

        self._last_root_size = current_size

        # Window resize can trigger many hover transitions under cursor.
        ToolTip.suspend_events_for(220)
        self._lock_layout_for_live_resize()
        self._schedule_window_transform_end()

    def _lock_layout_for_live_resize(self) -> None:
        if self._layout_lock_active:
            return

        self._layout_lock_active = True

    def _schedule_window_transform_end(self) -> None:
        if self._window_transform_end_job is not None:
            self.root.after_cancel(self._window_transform_end_job)
        self._window_transform_end_job = self.root.after(170, self._on_window_transform_end)

    def _on_window_transform_end(self) -> None:
        self._window_transform_end_job = None
        if not self._layout_lock_active:
            return

        self._layout_lock_active = False

        self._schedule_preview_resize()

    def _on_preview_container_resize(self, _event=None) -> None:
        if self._layout_lock_active:
            return
        if not self.auto_preview_var.get():
            return

        new_size = (
            self.preview_image_label.winfo_width(),
            self.preview_image_label.winfo_height(),
        )
        if new_size[0] <= 1 or new_size[1] <= 1:
            return
        if new_size == self._last_preview_size:
            return
        self._last_preview_size = new_size
        self._schedule_preview_resize()

    def _schedule_preview_resize(self) -> None:
        if self._resize_preview_job_id is not None:
            self.root.after_cancel(self._resize_preview_job_id)
        self._resize_preview_job_id = self.root.after(260, self._refresh_preview_from_cache)

    def _refresh_preview_from_cache(self) -> None:
        self._resize_preview_job_id = None
        if self._preview_source_image is None or self._preview_ctk_image is None:
            return

        target_size = self._compute_preview_size(self._preview_source_image)
        if target_size == self._last_preview_render_size:
            return

        self._last_preview_render_size = target_size
        self._preview_ctk_image.configure(size=target_size)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def _set_status(self, text: str, is_error: bool = False) -> None:
        if is_error:
            self.status_label.configure(
                text=text,
                fg_color=("#fbe4e4", "#3b1f1f"),
                text_color=("#7f1d1d", "#fecaca"),
            )
        else:
            self.status_label.configure(
                text=text,
                fg_color=("#edf2ff", "#1c2432"),
                text_color=("#213153", "#c7d2fe"),
            )


def create_root() -> tk.Misc:
    if TkinterDnD is None:
        return ctk.CTk()

    try:
        class CTkDndWindow(TkinterDnD.DnDWrapper, ctk.CTk):
            def __init__(self, *args, **kwargs):
                ctk.CTk.__init__(self, *args, **kwargs)
                TkinterDnD.DnDWrapper.__init__(self)

        return CTkDndWindow()
    except Exception:
        return ctk.CTk()


def run_app() -> int:
    root = create_root()
    QrStudioApp(root)
    root.mainloop()
    return 0
