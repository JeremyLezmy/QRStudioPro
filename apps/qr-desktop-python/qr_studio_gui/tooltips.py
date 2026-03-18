from __future__ import annotations

import time
import tkinter as tk
from typing import Optional


class ToolTip:
    """Modern-looking tooltip that appears on hover after a short delay."""
    _suspend_until_ts: float = 0.0

    @classmethod
    def suspend_events_for(cls, ms: int = 180) -> None:
        cls._suspend_until_ts = max(
            cls._suspend_until_ts,
            time.monotonic() + (ms / 1000.0),
        )

    def __init__(self, widget: tk.Widget, text: str, delay_ms: int = 350):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.tip_window: Optional[tk.Toplevel] = None
        self._job: Optional[str] = None

        self.widget.bind("<Enter>", self._schedule, add=True)
        self.widget.bind("<Leave>", self._hide, add=True)
        self.widget.bind("<ButtonPress>", self._hide, add=True)

    def _schedule(self, _event=None):
        if time.monotonic() < self._suspend_until_ts:
            return
        self._cancel()
        self._job = self.widget.after(self.delay_ms, self._show)

    def _cancel(self):
        if self._job is not None:
            self.widget.after_cancel(self._job)
            self._job = None

    def _show(self):
        if self.tip_window is not None or not self.text.strip():
            return

        x = self.widget.winfo_rootx() + 18
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6

        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        # Prevent tooltip from covering screen edges
        tw.update_idletasks()

        frame = tk.Frame(
            tw,
            background="#1e293b",
            highlightbackground="#334155",
            highlightthickness=1,
            padx=0,
            pady=0,
        )
        frame.pack()

        label = tk.Label(
            frame,
            text=self.text,
            justify="left",
            background="#1e293b",
            foreground="#e2e8f0",
            relief="flat",
            padx=10,
            pady=7,
            font=("Segoe UI", 9),
            wraplength=400,
        )
        label.pack()

    def _hide(self, _event=None):
        self._cancel()
        if self.tip_window is not None:
            self.tip_window.destroy()
            self.tip_window = None
