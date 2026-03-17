from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from typing import Any, Dict, Optional

import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from PIL import Image, ImageTk

from qr_presets import GraphicConfig, get_preset_graphic_config, list_presets

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ModuleNotFoundError:
    DND_FILES = None
    TkinterDnD = None


STYLE_MODE_VALUES = ["black_bg_safe", "full_dark_artistic", "white_clean"]
OPTIONAL_TUPLE_FIELDS = {"gradient_mix_base_rgb"}


class QrGuiApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("QR Designer")
        self.root.geometry("1320x860")
        self.root.minsize(1080, 720)

        self.url_var = tk.StringVar(value="https://phusis.io/")
        self.preset_var = tk.StringVar(value="black_bg_safe")
        self.logo_var = tk.StringVar(value=self._initial_logo_path())
        self.output_var = tk.StringVar(value="generated_qrcode/qr_output.png")
        self.decode_var = tk.BooleanVar(value=True)
        self.quiet_var = tk.BooleanVar(value=False)

        self.graphic_vars: Dict[str, tk.Variable] = {}
        self._preview_photo: Optional[ImageTk.PhotoImage] = None

        self._build_layout()
        self._load_preset_into_controls(self.preset_var.get())

    def _initial_logo_path(self) -> str:
        candidate = Path("logo_phusis.png")
        return str(candidate) if candidate.exists() else ""

    def _build_layout(self) -> None:
        root_frame = ttk.Frame(self.root, padding=10)
        root_frame.pack(fill="both", expand=True)

        paned = ttk.Panedwindow(root_frame, orient="horizontal")
        paned.pack(fill="both", expand=True)

        left = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=3)
        paned.add(right, weight=2)

        self._build_top_controls(left)
        self._build_graphic_controls(left)
        self._build_preview_panel(right)

    def _build_top_controls(self, parent: ttk.Frame) -> None:
        box = ttk.LabelFrame(parent, text="Parametres", padding=10)
        box.pack(fill="x", pady=(0, 8))

        ttk.Label(box, text="URL").grid(row=0, column=0, sticky="w")
        ttk.Entry(box, textvariable=self.url_var, width=78).grid(
            row=0, column=1, columnspan=6, sticky="ew", padx=(6, 0)
        )

        ttk.Label(box, text="Preset").grid(row=1, column=0, sticky="w", pady=(8, 0))
        preset_combo = ttk.Combobox(
            box,
            textvariable=self.preset_var,
            values=list_presets(),
            width=26,
            state="readonly",
        )
        preset_combo.grid(row=1, column=1, sticky="w", padx=(6, 0), pady=(8, 0))
        preset_combo.bind("<<ComboboxSelected>>", self._on_preset_changed)

        ttk.Button(box, text="Recharger Preset", command=self._reload_current_preset).grid(
            row=1, column=2, sticky="w", padx=(8, 0), pady=(8, 0)
        )

        ttk.Label(box, text="Logo").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(box, textvariable=self.logo_var, width=60).grid(
            row=2, column=1, columnspan=3, sticky="ew", padx=(6, 0), pady=(8, 0)
        )
        ttk.Button(box, text="Parcourir", command=self._pick_logo).grid(
            row=2, column=4, sticky="w", padx=(8, 0), pady=(8, 0)
        )
        ttk.Button(box, text="Sans Logo", command=lambda: self.logo_var.set("")).grid(
            row=2, column=5, sticky="w", padx=(6, 0), pady=(8, 0)
        )

        self.drop_label = ttk.Label(
            box,
            text="Drop Logo Ici",
            anchor="center",
            relief="solid",
            padding=8,
            width=20,
        )
        self.drop_label.grid(row=2, column=6, sticky="ew", padx=(8, 0), pady=(8, 0))

        ttk.Label(box, text="Sortie").grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(box, textvariable=self.output_var, width=60).grid(
            row=3, column=1, columnspan=3, sticky="ew", padx=(6, 0), pady=(8, 0)
        )
        ttk.Button(box, text="Choisir", command=self._pick_output).grid(
            row=3, column=4, sticky="w", padx=(8, 0), pady=(8, 0)
        )

        ttk.Checkbutton(box, text="Decode Check", variable=self.decode_var).grid(
            row=4, column=1, sticky="w", pady=(10, 0)
        )
        ttk.Checkbutton(box, text="Quiet Logs", variable=self.quiet_var).grid(
            row=4, column=2, sticky="w", pady=(10, 0)
        )

        ttk.Button(box, text="Apercu", command=self._render_preview).grid(
            row=4, column=4, sticky="e", padx=(8, 0), pady=(10, 0)
        )
        ttk.Button(box, text="Generer PNG", command=self._save_qr).grid(
            row=4, column=5, sticky="e", padx=(8, 0), pady=(10, 0)
        )

        box.columnconfigure(1, weight=1)
        box.columnconfigure(6, weight=1)

        self._init_drag_and_drop()

    def _build_graphic_controls(self, parent: ttk.Frame) -> None:
        wrap = ttk.LabelFrame(parent, text="GraphicConfig (tweak complet)", padding=6)
        wrap.pack(fill="both", expand=True)

        canvas = tk.Canvas(wrap, highlightthickness=0)
        scrollbar = ttk.Scrollbar(wrap, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)

        inner.bind(
            "<Configure>",
            lambda _evt: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for idx, f in enumerate(fields(GraphicConfig)):
            self._create_field_control(inner, idx, f.name, getattr(GraphicConfig(), f.name))

        # Quick access near logo options.
        keep_var = self.graphic_vars.get("logo_keep_original")
        if isinstance(keep_var, tk.BooleanVar):
            ttk.Checkbutton(
                self.drop_label.master,
                text="Garder Logo Intact",
                variable=keep_var,
            ).grid(row=2, column=7, sticky="w", padx=(8, 0), pady=(8, 0))

    def _build_preview_panel(self, parent: ttk.Frame) -> None:
        preview_box = ttk.LabelFrame(parent, text="Apercu", padding=10)
        preview_box.pack(fill="both", expand=True)

        self.preview_info_label = ttk.Label(
            preview_box,
            text="Clique sur Apercu pour voir le rendu",
            anchor="w",
        )
        self.preview_info_label.pack(fill="x", pady=(0, 8))

        self.preview_label = ttk.Label(preview_box, anchor="center", relief="solid")
        self.preview_label.pack(fill="both", expand=True)

    def _create_field_control(self, parent: ttk.Frame, row: int, field_name: str, default_value: Any) -> None:
        label_text = field_name.replace("_", " ")
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=3)

        if field_name == "style_mode":
            var = tk.StringVar(value=str(default_value))
            widget = ttk.Combobox(
                parent,
                textvariable=var,
                values=STYLE_MODE_VALUES,
                width=28,
                state="readonly",
            )
            widget.grid(row=row, column=1, sticky="ew", pady=3)
            self.graphic_vars[field_name] = var
            return

        if isinstance(default_value, bool):
            var = tk.BooleanVar(value=default_value)
            ttk.Checkbutton(parent, variable=var).grid(row=row, column=1, sticky="w", pady=3)
            self.graphic_vars[field_name] = var
            return

        initial_text = self._serialize_value(field_name, default_value)
        var = tk.StringVar(value=initial_text)

        ttk.Entry(parent, textvariable=var, width=32).grid(row=row, column=1, sticky="ew", pady=3)
        self.graphic_vars[field_name] = var

        if self._is_color_field(default_value):
            ttk.Button(
                parent,
                text="Palette",
                command=lambda n=field_name: self._choose_color(n),
            ).grid(row=row, column=2, sticky="w", padx=(6, 0), pady=3)

        parent.columnconfigure(1, weight=1)

    def _init_drag_and_drop(self) -> None:
        if not TkinterDnD or not DND_FILES:
            self.drop_label.configure(text="Drop indisponible\n(installe tkinterdnd2)")
            return

        self.drop_label.drop_target_register(DND_FILES)
        self.drop_label.dnd_bind("<<Drop>>", self._on_logo_drop)

    def _on_logo_drop(self, event: tk.Event) -> None:
        dropped = self.root.tk.splitlist(event.data)
        if not dropped:
            return

        path = dropped[0].strip()
        if path.startswith("{") and path.endswith("}"):
            path = path[1:-1]

        self.logo_var.set(path)

    def _pick_logo(self) -> None:
        selected = filedialog.askopenfilename(
            title="Selectionne un logo",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.gif *.svg"), ("Tous", "*.*")],
        )
        if selected:
            self.logo_var.set(selected)

    def _pick_output(self) -> None:
        selected = filedialog.asksaveasfilename(
            title="Chemin de sortie",
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("Tous", "*.*")],
            initialfile=Path(self.output_var.get() or "generated_qrcode/qr_output.png").name,
        )
        if selected:
            self.output_var.set(selected)

    def _on_preset_changed(self, _evt: tk.Event) -> None:
        self._load_preset_into_controls(self.preset_var.get())

    def _reload_current_preset(self) -> None:
        self._load_preset_into_controls(self.preset_var.get())

    def _load_preset_into_controls(self, preset_name: str) -> None:
        cfg = get_preset_graphic_config(preset_name)
        for f in fields(GraphicConfig):
            value = getattr(cfg, f.name)
            var = self.graphic_vars.get(f.name)
            if var is None:
                continue
            if isinstance(var, tk.BooleanVar):
                var.set(bool(value))
            else:
                var.set(self._serialize_value(f.name, value))

    def _is_color_field(self, value: Any) -> bool:
        return isinstance(value, tuple) and len(value) in (3, 4)

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
            raise ValueError(f"{expected_len} valeurs attendues, recu: {raw}")

        values: list[int] = []
        for p in parts:
            i = int(p)
            if clamp_as_color and (i < 0 or i > 255):
                raise ValueError("Les composantes couleur doivent etre entre 0 et 255")
            values.append(i)

        return tuple(values)

    def _collect_graphic_overrides(self) -> Dict[str, Any]:
        base = GraphicConfig()
        overrides: Dict[str, Any] = {}

        for f in fields(GraphicConfig):
            default_value = getattr(base, f.name)
            var = self.graphic_vars[f.name]

            if isinstance(var, tk.BooleanVar):
                overrides[f.name] = bool(var.get())
                continue

            raw = str(var.get()).strip()

            if isinstance(default_value, tuple):
                overrides[f.name] = self._parse_tuple(
                    raw,
                    expected_len=len(default_value),
                    allow_none=f.name in OPTIONAL_TUPLE_FIELDS,
                    clamp_as_color=self._is_color_field(default_value),
                )
            elif isinstance(default_value, int):
                overrides[f.name] = int(raw)
            elif isinstance(default_value, float):
                overrides[f.name] = float(raw)
            else:
                overrides[f.name] = raw

        return overrides

    def _choose_color(self, field_name: str) -> None:
        var = self.graphic_vars.get(field_name)
        if not isinstance(var, tk.StringVar):
            return

        current = var.get().strip()
        allow_none = field_name in OPTIONAL_TUPLE_FIELDS
        if allow_none and current.lower() in {"", "none", "null"}:
            base = (128, 128, 128)
            alpha = 255
            length = 3
        else:
            raw_tuple = self._parse_tuple(
                current,
                4 if current.count(",") == 3 else 3,
                allow_none=False,
                clamp_as_color=True,
            )
            if raw_tuple is None:
                return
            length = len(raw_tuple)
            alpha = raw_tuple[3] if length == 4 else 255
            base = raw_tuple[:3]

        color = colorchooser.askcolor(color="#%02x%02x%02x" % base, title=f"Choisir {field_name}")
        if not color or color[0] is None:
            return

        rgb = tuple(int(v) for v in color[0])
        if length == 4:
            var.set(f"{rgb[0]},{rgb[1]},{rgb[2]},{alpha}")
        else:
            var.set(f"{rgb[0]},{rgb[1]},{rgb[2]}")

    def _resolve_logo_path(self) -> Optional[Path]:
        raw = self.logo_var.get().strip()
        if raw.lower() in {"", "none", "null", "sans"}:
            return None
        return Path(raw)

    def _build_runtime_config(self):
        url = self.url_var.get().strip()
        if not url:
            raise ValueError("L'URL est obligatoire")

        output = self.output_var.get().strip()
        if not output:
            raise ValueError("Le chemin de sortie est obligatoire")

        from generate_qrcode import create_qr_config

        graphic_overrides = self._collect_graphic_overrides()

        return create_qr_config(
            url=url,
            preset_name=self.preset_var.get().strip() or None,
            logo_path=self._resolve_logo_path(),
            output_path=Path(output),
            graphic_overrides=graphic_overrides,
            run_decode_check=self.decode_var.get(),
            verbose=not self.quiet_var.get(),
        )

    def _render_preview(self) -> None:
        try:
            from generate_qrcode import BrandedQRGenerator

            cfg = self._build_runtime_config()
            image = BrandedQRGenerator(cfg).render()
        except Exception as exc:
            messagebox.showerror("Erreur preview", str(exc))
            return

        preview = image.copy()
        preview.thumbnail((540, 540), Image.LANCZOS)

        self._preview_photo = ImageTk.PhotoImage(preview)
        self.preview_label.configure(image=self._preview_photo)
        self.preview_info_label.configure(text=f"Apercu: {image.width}x{image.height}")

    def _save_qr(self) -> None:
        try:
            from generate_qrcode import BrandedQRGenerator

            cfg = self._build_runtime_config()
            BrandedQRGenerator(cfg).save()
        except Exception as exc:
            messagebox.showerror("Erreur generation", str(exc))
            return

        self._render_preview()
        messagebox.showinfo("Succes", f"QR code genere dans:\n{cfg.output_path}")


def main() -> int:
    root_cls = TkinterDnD.Tk if TkinterDnD else tk.Tk
    root = root_cls()
    QrGuiApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
