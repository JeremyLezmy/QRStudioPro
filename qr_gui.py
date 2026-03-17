from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from typing import Any, Dict, Optional

import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox

try:
    import customtkinter as ctk
except ModuleNotFoundError as exc:
    raise SystemExit(
        "customtkinter est requis. Installe-le avec: pip install customtkinter"
    ) from exc

from PIL import Image, ImageTk

from qr_presets import GraphicConfig, get_preset_graphic_config, list_presets

try:
    from tkinterdnd2 import DND_FILES
except ModuleNotFoundError:
    DND_FILES = None


STYLE_MODE_VALUES = ["black_bg_safe", "full_dark_artistic", "white_clean"]
OPTIONAL_TUPLE_FIELDS = {"gradient_mix_base_rgb"}


class ProfessionalQrGuiApp:
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title("QR Studio")
        self.root.geometry("1540x920")
        self.root.minsize(1220, 760)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        self.url_var = tk.StringVar(value="https://phusis.io/")
        self.preset_var = tk.StringVar(value="black_bg_safe")
        self.logo_var = tk.StringVar(value=self._initial_logo_path())
        self.output_var = tk.StringVar(value="generated_qrcode/qr_output.png")

        self.decode_var = tk.BooleanVar(value=True)
        self.quiet_var = tk.BooleanVar(value=False)
        self.auto_preview_var = tk.BooleanVar(value=True)

        self.graphic_vars: Dict[str, tk.Variable] = {}
        self._preview_photo: Optional[ImageTk.PhotoImage] = None
        self._preview_job_id: Optional[str] = None

        self._build_ui()
        self._load_preset_into_controls(self.preset_var.get())
        self._register_auto_preview_watchers()
        self._schedule_auto_preview()

    def _initial_logo_path(self) -> str:
        candidate = Path("logo_phusis.png")
        return str(candidate) if candidate.exists() else ""

    # ---------------------------------------------------------------------
    # UI
    # ---------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.root.grid_columnconfigure(0, weight=5)
        self.root.grid_columnconfigure(1, weight=6)
        self.root.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(self.root, corner_radius=16)
        right = ctk.CTkFrame(self.root, corner_radius=16)
        left.grid(row=0, column=0, sticky="nsew", padx=(14, 8), pady=14)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 14), pady=14)

        self._build_left_panel(left)
        self._build_right_panel(right)

    def _build_left_panel(self, parent: ctk.CTkFrame) -> None:
        parent.grid_rowconfigure(3, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            parent,
            text="QR Studio V2",
            font=ctk.CTkFont(size=26, weight="bold"),
            anchor="w",
        )
        title.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))

        basics = ctk.CTkFrame(parent, corner_radius=12)
        basics.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))
        basics.grid_columnconfigure(1, weight=1)
        basics.grid_columnconfigure(2, weight=0)

        ctk.CTkLabel(basics, text="URL", anchor="w").grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))
        self.url_entry = ctk.CTkEntry(basics, textvariable=self.url_var)
        self.url_entry.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(4, 12), pady=(10, 6))

        ctk.CTkLabel(basics, text="Preset", anchor="w").grid(row=1, column=0, sticky="w", padx=12, pady=6)
        self.preset_menu = ctk.CTkOptionMenu(
            basics,
            variable=self.preset_var,
            values=list_presets(),
            command=self._on_preset_change,
            dynamic_resizing=False,
            width=220,
        )
        self.preset_menu.grid(row=1, column=1, sticky="w", padx=(4, 8), pady=6)
        ctk.CTkButton(
            basics,
            text="Reload Preset",
            width=120,
            command=self._reload_current_preset,
        ).grid(row=1, column=2, sticky="e", padx=(0, 12), pady=6)

        ctk.CTkLabel(basics, text="Logo", anchor="w").grid(row=2, column=0, sticky="w", padx=12, pady=6)
        self.logo_entry = ctk.CTkEntry(basics, textvariable=self.logo_var)
        self.logo_entry.grid(row=2, column=1, sticky="ew", padx=(4, 8), pady=6)
        logo_actions = ctk.CTkFrame(basics, fg_color="transparent")
        logo_actions.grid(row=2, column=2, sticky="e", padx=(0, 12), pady=6)
        ctk.CTkButton(logo_actions, text="Browse", width=76, command=self._pick_logo).grid(
            row=0, column=0, padx=(0, 6)
        )
        ctk.CTkButton(logo_actions, text="Clear", width=56, command=lambda: self.logo_var.set("")).grid(
            row=0, column=1
        )

        ctk.CTkLabel(basics, text="Output", anchor="w").grid(row=3, column=0, sticky="w", padx=12, pady=6)
        self.output_entry = ctk.CTkEntry(basics, textvariable=self.output_var)
        self.output_entry.grid(row=3, column=1, sticky="ew", padx=(4, 8), pady=6)
        ctk.CTkButton(
            basics,
            text="Choose",
            width=120,
            command=self._pick_output,
        ).grid(row=3, column=2, sticky="e", padx=(0, 12), pady=6)

        self.drop_hint_label = ctk.CTkLabel(
            basics,
            text="Drop logo file here",
            corner_radius=8,
            fg_color=("#d7dbe2", "#2c3139"),
            text_color=("#1f2430", "#d9e0ee"),
            height=34,
        )
        self.drop_hint_label.grid(row=4, column=0, columnspan=3, sticky="ew", padx=12, pady=(6, 10))

        quick = ctk.CTkFrame(parent, corner_radius=12)
        quick.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))
        quick.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        ctk.CTkSwitch(quick, text="Auto Preview", variable=self.auto_preview_var).grid(
            row=0, column=0, sticky="w", padx=10, pady=10
        )
        ctk.CTkSwitch(quick, text="Decode Check", variable=self.decode_var).grid(
            row=0, column=1, sticky="w", padx=10, pady=10
        )
        ctk.CTkSwitch(quick, text="Quiet Logs", variable=self.quiet_var).grid(
            row=0, column=2, sticky="w", padx=10, pady=10
        )
        ctk.CTkButton(quick, text="Preview", command=self._render_preview_manual).grid(
            row=0, column=4, sticky="e", padx=10, pady=10
        )
        ctk.CTkButton(quick, text="Generate PNG", command=self._save_qr).grid(
            row=0, column=5, sticky="e", padx=(2, 10), pady=10
        )

        config_card = ctk.CTkFrame(parent, corner_radius=12)
        config_card.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 12))
        config_card.grid_rowconfigure(1, weight=1)
        config_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            config_card,
            text="Graphic Config (full tweak)",
            anchor="w",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 8))

        self.config_scroll = ctk.CTkScrollableFrame(config_card, corner_radius=10)
        self.config_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.config_scroll.grid_columnconfigure(1, weight=1)

        default_graphic = GraphicConfig()
        for idx, f in enumerate(fields(GraphicConfig)):
            self._create_graphic_field_control(
                self.config_scroll,
                idx,
                f.name,
                getattr(default_graphic, f.name),
            )

        keep_logo_var = self.graphic_vars.get("logo_keep_original")
        if isinstance(keep_logo_var, tk.BooleanVar):
            ctk.CTkSwitch(
                quick,
                text="Keep Logo Original",
                variable=keep_logo_var,
                command=self._schedule_auto_preview,
            ).grid(row=0, column=3, sticky="w", padx=10, pady=10)

        self._setup_drag_and_drop()

    def _build_right_panel(self, parent: ctk.CTkFrame) -> None:
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            parent,
            text="Live Preview",
            font=ctk.CTkFont(size=22, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))

        self.preview_card = ctk.CTkFrame(parent, corner_radius=12)
        self.preview_card.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))
        self.preview_card.grid_rowconfigure(1, weight=1)
        self.preview_card.grid_columnconfigure(0, weight=1)

        self.preview_meta_label = ctk.CTkLabel(
            self.preview_card,
            text="Waiting for first render...",
            anchor="w",
            text_color=("#2f3847", "#a9b4c8"),
        )
        self.preview_meta_label.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))

        self.preview_image_label = ctk.CTkLabel(
            self.preview_card,
            text="",
            fg_color=("#f5f7fb", "#111519"),
            corner_radius=10,
        )
        self.preview_image_label.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self.status_label = ctk.CTkLabel(
            parent,
            text="Ready",
            anchor="w",
            corner_radius=8,
            fg_color=("#ecf2ff", "#1d2430"),
            text_color=("#1f2e4d", "#c5d5f2"),
        )
        self.status_label.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12), ipady=8)

    def _create_graphic_field_control(
        self,
        parent: ctk.CTkScrollableFrame,
        row: int,
        field_name: str,
        default_value: Any,
    ) -> None:
        label = ctk.CTkLabel(parent, text=field_name.replace("_", " "), anchor="w")
        label.grid(row=row, column=0, sticky="w", padx=(4, 8), pady=5)

        if field_name == "style_mode":
            var = tk.StringVar(value=str(default_value))
            control = ctk.CTkOptionMenu(
                parent,
                variable=var,
                values=STYLE_MODE_VALUES,
                dynamic_resizing=False,
                width=220,
                command=lambda _v: self._schedule_auto_preview(),
            )
            control.grid(row=row, column=1, sticky="w", pady=5)
            self.graphic_vars[field_name] = var
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
            return

        var = tk.StringVar(value=self._serialize_value(field_name, default_value))
        entry = ctk.CTkEntry(parent, textvariable=var)
        entry.grid(row=row, column=1, sticky="ew", pady=5)
        self.graphic_vars[field_name] = var

        if self._is_color_field(default_value, field_name):
            ctk.CTkButton(
                parent,
                text="Palette",
                width=78,
                command=lambda n=field_name: self._choose_color(n),
            ).grid(row=row, column=2, sticky="w", padx=(8, 4), pady=5)

    # ---------------------------------------------------------------------
    # DnD
    # ---------------------------------------------------------------------

    def _setup_drag_and_drop(self) -> None:
        if DND_FILES is None:
            self.drop_hint_label.configure(text="Drag and drop unavailable (install tkinterdnd2)")
            return

        target_widgets = [self.drop_hint_label, self.logo_entry]

        ok = False
        for widget in target_widgets:
            if not hasattr(widget, "drop_target_register") or not hasattr(widget, "dnd_bind"):
                continue
            try:
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", self._on_logo_drop)
                ok = True
            except Exception:
                continue

        if ok:
            self.drop_hint_label.configure(text="Drop logo file here")
        else:
            self.drop_hint_label.configure(text="Drag and drop unavailable in this runtime")

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
        self._set_status(f"Logo loaded via drop: {path}")
        self._schedule_auto_preview()

    # ---------------------------------------------------------------------
    # Parsing
    # ---------------------------------------------------------------------

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

        values: list[int] = []
        for p in parts:
            i = int(p)
            if clamp_as_color and (i < 0 or i > 255):
                raise ValueError("Color values must be in [0, 255]")
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
                    clamp_as_color=self._is_color_field(default_value, f.name),
                )
            elif isinstance(default_value, int):
                overrides[f.name] = int(raw)
            elif isinstance(default_value, float):
                overrides[f.name] = float(raw)
            else:
                overrides[f.name] = raw

        return overrides

    # ---------------------------------------------------------------------
    # Actions
    # ---------------------------------------------------------------------

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

    def _resolve_logo_path(self) -> Optional[Path]:
        raw = self.logo_var.get().strip()
        if raw.lower() in {"", "none", "null", "sans"}:
            return None
        return Path(raw)

    def _build_runtime_config(self):
        url = self.url_var.get().strip()
        if not url:
            raise ValueError("URL is required")

        output = self.output_var.get().strip()
        if not output:
            raise ValueError("Output path is required")

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

    def _render_preview(self, show_errors: bool) -> None:
        try:
            from generate_qrcode import BrandedQRGenerator

            cfg = self._build_runtime_config()
            image = BrandedQRGenerator(cfg).render()
        except Exception as exc:
            self._set_status(f"Preview not updated: {exc}", is_error=True)
            if show_errors:
                messagebox.showerror("Preview error", str(exc))
            return

        preview = image.copy()
        preview.thumbnail((840, 840), Image.LANCZOS)

        self._preview_photo = ImageTk.PhotoImage(preview)
        self.preview_image_label.configure(image=self._preview_photo)
        self.preview_meta_label.configure(
            text=f"Preset: {cfg.graphic.style_mode} | Canvas: {image.width}x{image.height}"
        )
        self._set_status("Preview updated")

    def _render_preview_manual(self) -> None:
        self._render_preview(show_errors=True)

    def _render_preview_silent(self) -> None:
        self._preview_job_id = None
        self._render_preview(show_errors=False)

    def _save_qr(self) -> None:
        try:
            from generate_qrcode import BrandedQRGenerator

            cfg = self._build_runtime_config()
            BrandedQRGenerator(cfg).save()
        except Exception as exc:
            self._set_status(f"Generation failed: {exc}", is_error=True)
            messagebox.showerror("Generation error", str(exc))
            return

        self._set_status(f"Generated: {cfg.output_path}")
        self._render_preview(show_errors=False)
        messagebox.showinfo("Success", f"QR generated:\n{cfg.output_path}")

    def _choose_color(self, field_name: str) -> None:
        var = self.graphic_vars.get(field_name)
        if not isinstance(var, tk.StringVar):
            return

        current = var.get().strip()
        allow_none = field_name in OPTIONAL_TUPLE_FIELDS

        if allow_none and current.lower() in {"", "none", "null"}:
            base = (128, 128, 128)
            alpha = 255
            components = 3
        else:
            components = 4 if current.count(",") == 3 else 3
            raw_tuple = self._parse_tuple(
                current,
                expected_len=components,
                allow_none=False,
                clamp_as_color=True,
            )
            if raw_tuple is None:
                return
            base = raw_tuple[:3]
            alpha = raw_tuple[3] if len(raw_tuple) == 4 else 255

        color = colorchooser.askcolor(color="#%02x%02x%02x" % base, title=f"Choose {field_name}")
        if not color or color[0] is None:
            return

        rgb = tuple(int(v) for v in color[0])
        if components == 4:
            var.set(f"{rgb[0]},{rgb[1]},{rgb[2]},{alpha}")
        else:
            var.set(f"{rgb[0]},{rgb[1]},{rgb[2]}")

        self._schedule_auto_preview()

    # ---------------------------------------------------------------------
    # Presets and auto preview
    # ---------------------------------------------------------------------

    def _on_preset_change(self, _selected: str) -> None:
        self._load_preset_into_controls(self.preset_var.get())
        self._set_status(f"Preset loaded: {self.preset_var.get()}")
        self._schedule_auto_preview()

    def _reload_current_preset(self) -> None:
        self._load_preset_into_controls(self.preset_var.get())
        self._set_status(f"Preset reloaded: {self.preset_var.get()}")
        self._schedule_auto_preview()

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

    def _register_auto_preview_watchers(self) -> None:
        tracked_vars = [
            self.url_var,
            self.logo_var,
            self.output_var,
            self.preset_var,
            self.auto_preview_var,
        ]
        tracked_vars.extend(self.graphic_vars.values())

        for var in tracked_vars:
            var.trace_add("write", self._on_any_input_changed)

    def _on_any_input_changed(self, *_args) -> None:
        self._schedule_auto_preview()

    def _schedule_auto_preview(self) -> None:
        if not self.auto_preview_var.get():
            if self._preview_job_id is not None:
                self.root.after_cancel(self._preview_job_id)
                self._preview_job_id = None
            return

        if self._preview_job_id is not None:
            self.root.after_cancel(self._preview_job_id)

        self._preview_job_id = self.root.after(320, self._render_preview_silent)

    # ---------------------------------------------------------------------
    # Status
    # ---------------------------------------------------------------------

    def _set_status(self, text: str, is_error: bool = False) -> None:
        if is_error:
            self.status_label.configure(
                text=text,
                fg_color=("#fbe3e3", "#3b2020"),
                text_color=("#7a1e1e", "#f5b0b0"),
            )
        else:
            self.status_label.configure(
                text=text,
                fg_color=("#ecf2ff", "#1d2430"),
                text_color=("#1f2e4d", "#c5d5f2"),
            )


def main() -> int:
    root = ctk.CTk()
    ProfessionalQrGuiApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
