"""Native Tk desktop workbench for composing and testing AC conjectures.

This interface calls the research engine in-process. The browser workbench is
still available through ``ac-workbench`` as a separate entry point.
"""

from __future__ import annotations

import json
import atexit
import os
import platform
import queue
import threading
import tkinter as tk
import traceback
from datetime import datetime, timezone
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from ac.gui.experiments import FAMILY_LIMITS, STATISTICS, run_experiment
from ac.gui.research_state import read_state, write_state
from ac.core.word import ChainWord
from ac.transform import (
    complement, hat, inverse_hat, inverse_prefix_lift, prefix_lift, reverse,
    restrict_positions, insert_position,
)
from ac.patterns.classical import ClassicalPattern


BG = "#f3f5f2"
PANEL = "#ffffff"
INK = "#18231f"
MUTED = "#66746e"
LINE = "#dce3de"
GREEN = "#176c52"
GREEN_DARK = "#10553f"
MINT = "#e7f3ed"
AMBER = "#a35b1b"
RED = "#a8443c"
FAMILIES = ("ordinary", "modified", "revised")
FAMILY_LABELS = {"ordinary": "Ordinary", "modified": "Modified", "revised": "Revised"}
FAMILY_CHOICES = {"ordinary": "Ordinary", "modified": "Modified", "revised": "Revised"}
FAMILY_DESCRIPTIONS = {
    "ordinary": "Ordinary: x₁=1; each later value is at most 2 plus the earlier ascent count. Example: 1, 2, 1.",
    "modified": "Modified: a Cayley word where every value first appears as an ascent top. Example: 1, 3, 3, 1, 2, 2.",
    "revised": "Revised: a Cayley word where every value first appears as an ascent bottom. Example: 2, 1, 2.",
}
STAT_DESCRIPTIONS = {
    "none": "Compare class totals only; do not split words by a statistic.",
    "ascents": "Count adjacent rises. Example: 1, 2, 1, 3, 2 has 2 ascents.",
    "ascent_runs": "Count ascent runs. Example: 1, 2, 1, 3, 2 has 3 runs.",
    "run_start_positions": "List run starts. Example: 1, 2, 1, 3, 2 → [1, 3, 5].",
    "run_lengths": "List run lengths. Example: 1, 2 | 1, 3 | 2 → [2, 2, 1].",
    "maximum": "Largest value. Example: max(1, 2, 1, 3, 2) = 3.",
    "distinct_values": "Number of different values. Example: 1, 2, 1, 3, 2 has 3.",
    "multiplicity_partition": "Value frequencies, sorted largest first. Example: [2, 2, 1].",
    "first_occurrence_positions": "Positions where new values first appear. Example: [1, 2, 4].",
    "last_occurrence_positions": "Final occurrence positions, left to right. Example: [3, 4, 5].",
}
TRANSFORM_DESCRIPTIONS = {
    "reverse": "Reverse positions. Example: 1, 2, 3, 1 → 1, 3, 2, 1.",
    "complement": "Replace v by height + 1 − v. At height 3: 1, 2, 3 → 3, 2, 1.",
    "hat": "Apply ordered prefix lifts at ascent tops. Example: 1, 2, 1, 2 → 1, 3, 1, 2.",
    "inverse_hat": "Partial inverse of the hat map. Example: 1, 3, 1, 2 → 1, 2, 1, 2.",
    "prefix_lift": "Click a pivot: earlier values at least xᵢ rise by 1. Example: L₂(2,1,2) = 3,1,2.",
    "inverse_prefix_lift": "Click a first-occurrence pivot to undo its lift. Example: L₂⁻¹(3,1,2) = 2,1,2.",
    "insert_position": "Click a cut to insert the chosen existing value after it. Cut 1 in 1,2,1 with value 2 gives 1,2,2,1.",
    "delete_position": "Click a position to remove it. In 1,2,2,1, deleting position 3 gives 1,2,1.",
}
PATTERNS = ("2122", "2212", "3121", "221", "121", "211")

_LOG_STREAM = None


def _startup_log_path() -> Path:
    if __import__("sys").platform == "darwin":
        return Path.home() / "Library" / "Logs" / "AscentCalculus" / "startup.log"
    return Path.home() / ".ascent-calculus" / "startup.log"


def _log(event: str, **details) -> None:
    if _LOG_STREAM is None:
        return
    record = {"time": datetime.now(timezone.utc).isoformat(), "event": event, **details}
    try:
        _LOG_STREAM.write(json.dumps(record, default=str, sort_keys=True) + "\n")
        _LOG_STREAM.flush()
    except OSError:
        pass


def _open_startup_log() -> Path | None:
    global _LOG_STREAM
    path = _startup_log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        _LOG_STREAM = path.open("a", encoding="utf-8", buffering=1)
        _log("process_started", pid=os.getpid(), platform=platform.platform(), architecture=platform.machine())
        atexit.register(lambda: _log("process_exit"))
        return path
    except OSError:
        _LOG_STREAM = None
        return None


def _side(family: str, rules: list[dict[str, Any]]) -> dict[str, Any]:
    return {"family": family, "degree_offset": 0, "rules": rules}


def _family_key(value: str) -> str:
    for key, label in FAMILY_CHOICES.items():
        if value == label:
            return key
    return value


class HoverTip:
    """Small native hover/focus help that keeps the main surface uncluttered."""

    def __init__(self, widget, text):
        self.widget, self.text = widget, text
        self.window = None
        self.pending = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<FocusIn>", self._schedule, add="+")
        widget.bind("<FocusOut>", self.hide, add="+")

    def _schedule(self, _event=None):
        self.cancel()
        self.pending = self.widget.after(420, self.show)

    def cancel(self):
        if self.pending:
            try:
                self.widget.after_cancel(self.pending)
            except tk.TclError:
                pass
            self.pending = None

    def show(self):
        self.pending = None
        try:
            text = self.text() if callable(self.text) else self.text
            if not text or not self.widget.winfo_exists():
                return
            if self.window is None or not self.window.winfo_exists():
                self.window = tk.Toplevel(self.widget)
                self.window.withdraw()
                self.window.overrideredirect(True)
                self.window.attributes("-topmost", True)
                self.label = tk.Label(self.window, text=text, bg="#173544", fg="#f5f6f3", justify="left", anchor="w", wraplength=330, padx=11, pady=8, font=("TkDefaultFont", 9))
                self.label.pack()
            else:
                self.label.configure(text=text)
            self.window.update_idletasks()
            x = min(self.widget.winfo_rootx(), self.widget.winfo_screenwidth() - self.window.winfo_reqwidth() - 10)
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 7
            if y + self.window.winfo_reqheight() > self.widget.winfo_screenheight() - 10:
                y = max(10, self.widget.winfo_rooty() - self.window.winfo_reqheight() - 7)
            self.window.geometry(f"+{max(10, x)}+{max(10, y)}")
            self.window.deiconify()
        except tk.TclError:
            self.hide()

    def hide(self, _event=None):
        self.cancel()
        if self.window is not None:
            try:
                self.window.withdraw()
            except tk.TclError:
                self.window = None


class DropLane(tk.Frame):
    """Native drop target accepting pattern blocks from the palette."""

    def __init__(self, master, app: "DesktopWorkbench", side: str):
        super().__init__(master, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        self.app, self.side = app, side
        self.bind("<Enter>", lambda _e: (setattr(self.app, "focused_side", self.side), self._highlight(True)))
        self.bind("<Leave>", lambda _e: self._highlight(False))
        self.bind("<Button-1>", lambda _e: setattr(self.app, "focused_side", self.side))
        self.columnconfigure(0, weight=1)
        self.family = ttk.Combobox(self, state="readonly", values=tuple(FAMILY_CHOICES.values()), width=15)
        self.family.set(FAMILY_CHOICES["modified"])
        title = "CLASS A" if side == "left" else "CLASS B"
        tk.Label(self, text=title, bg=PANEL, fg=INK, font=("TkDefaultFont", 9, "bold")).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 2))
        self.family.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 9))
        self.family.bind("<<ComboboxSelected>>", lambda _e: self.app.changed())
        HoverTip(self.family, lambda: self.app.family_description(self.family.get()))
        self.count = tk.Label(self, text="0 pattern rules", bg=PANEL, fg=MUTED, font=("TkDefaultFont", 9))
        self.count.grid(row=0, column=1, sticky="e", padx=14)
        self.chips = tk.Frame(self, bg=PANEL)
        self.chips.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10)
        self.empty = tk.Label(self, text="Drop a pattern here  ·  e.g.  ⟨2122⟩", bg="#f8faf8", fg="#87938d", font=("TkDefaultFont", 10), pady=14, highlightthickness=1, highlightbackground=LINE)
        self.empty.grid(row=3, column=0, columnspan=2, sticky="ew", padx=12, pady=(4, 12))
        HoverTip(self.empty, "Drop a family chip here to change the family, or drop a pattern to add the selected Avoid/Contain rule.")

    def _highlight(self, on: bool):
        self.configure(highlightbackground=GREEN if on else LINE, highlightthickness=2 if on else 1)

    def _contains(self, widget):
        while widget is not None:
            if widget is self:
                return True
            widget = getattr(widget, "master", None)
        return False

    def render(self):
        for child in self.chips.winfo_children():
            child.destroy()
        rules = self.app.rules[self.side]
        self.count.configure(text=f"{len(rules)} pattern rule{'s' if len(rules) != 1 else ''}")
        self.empty.grid() if not rules else self.empty.grid_remove()
        for index, rule in enumerate(rules):
            mode = rule["mode"]
            color = "#fff0e9" if mode == "avoid" else MINT
            fg = "#965233" if mode == "avoid" else GREEN_DARK
            chip = tk.Frame(self.chips, bg=color, highlightthickness=1, highlightbackground="#eadbd1" if mode == "avoid" else "#c9e2d5")
            chip.grid(row=index // 3, column=index % 3, sticky="w", padx=3, pady=3)
            tk.Label(chip, text=f"{mode.title()}  ⟨{', '.join(map(str, rule['pattern']))}⟩", bg=color, fg=fg, font=("TkDefaultFont", 9, "bold"), padx=8, pady=6).pack(side="left")
            tk.Button(chip, text="×", command=lambda i=index, s=self.side: self.app.remove_rule(s, i), relief="flat", borderwidth=0, bg=color, fg=fg, activebackground=color, font=("TkDefaultFont", 11), padx=7, cursor="hand2").pack(side="left")


class DesktopWorkbench:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Ascent Engine")
        screen_width, screen_height = root.winfo_screenwidth(), root.winfo_screenheight()
        self.compact_layout = screen_height < 850
        window_width = min(1320, max(900, screen_width - 48))
        window_height = min(820, max(640, screen_height - 40))
        root.geometry(f"{window_width}x{window_height}")
        root.minsize(min(1040, window_width), min(680, window_height))
        self.root.configure(bg=BG)
        self.drag_payload = None
        self.focused_side = "left"
        self.rules = {"left": [], "right": []}
        self.saved_result = None
        self._save_timer = None
        self._worker_messages: queue.Queue = queue.Queue()
        self.state = read_state()
        self._style()
        self._build()
        self._restore_draft()
        self._refresh_conjecture()
        self.root.after(120, self._poll_worker)

    def _style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TCombobox", padding=6, fieldbackground=PANEL, background=PANEL, foreground=INK, bordercolor=LINE, arrowsize=12)
        style.map("TCombobox", fieldbackground=[("readonly", PANEL)], foreground=[("readonly", INK)])
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=INK, rowheight=28 if self.compact_layout else 34, bordercolor=LINE, font=("TkDefaultFont", 10))
        style.configure("Treeview.Heading", background="#f0f4f1", foreground=MUTED, relief="flat", font=("TkDefaultFont", 9, "bold"), padding=(8, 9))
        style.map("Treeview", background=[("selected", MINT)], foreground=[("selected", INK)])
        style.configure("Horizontal.TProgressbar", troughcolor="#e8eeea", background=GREEN, bordercolor="#e8eeea", lightcolor=GREEN, darkcolor=GREEN)

    def _build(self):
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)
        header = tk.Frame(self.root, bg=INK, height=64 if self.compact_layout else 76)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        tk.Label(header, text="A", bg=GREEN, fg="white", font=("TkDefaultFont", 15, "bold"), width=3, height=1).pack(side="left", padx=(24, 12), pady=12 if self.compact_layout else 18)
        titlebox = tk.Frame(header, bg=INK)
        titlebox.pack(side="left", pady=9 if self.compact_layout else 13)
        tk.Label(titlebox, text="Ascent Engine", bg=INK, fg="white", font=("TkDefaultFont", 17, "bold")).pack(anchor="w")
        tk.Label(titlebox, text="A workbench for sequence conjectures", bg=INK, fg="#b9cbc2", font=("TkDefaultFont", 9)).pack(anchor="w", pady=(2, 0))
        self.header_status = tk.Label(header, text="LOCAL · FINITE TESTS", bg=INK, fg="#b9cbc2", font=("TkDefaultFont", 9, "bold"))
        self.header_status.pack(side="right", padx=26)

        body = tk.Frame(self.root, bg=BG)
        body.grid(row=1, column=0, sticky="nsew", padx=22, pady=14 if self.compact_layout else 18)
        body.columnconfigure(0, weight=0, minsize=238)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=0)
        body.rowconfigure(1, weight=1)
        nav = tk.Frame(body, bg=BG)
        nav.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        self.nav_buttons = {}
        for key, label in (("conjecture", "Conjecture engine"), ("transform", "Transform visualizer")):
            button = tk.Button(nav, text=label, command=lambda k=key: self._show_view(k), relief="flat", bd=0, padx=14, pady=8, cursor="hand2", font=("TkDefaultFont", 9, "bold"))
            button.pack(side="left", padx=(0, 6))
            self.nav_buttons[key] = button
        content = tk.Frame(body, bg=BG)
        content.grid(row=1, column=0, columnspan=2, sticky="nsew")
        content.columnconfigure(0, weight=0, minsize=238)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)
        self.main_rail = self._build_palette(content)
        self.main_work = self._build_workspace(content)
        self.transform_view = self._build_transform_view(content)
        self._show_view("conjecture")

    def _build_palette(self, parent):
        rail = tk.Frame(parent, bg=BG, width=238)
        rail.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        rail.grid_propagate(False)
        tk.Label(rail, text="DRAG INTO A CLASS", bg=BG, fg=MUTED, font=("TkDefaultFont", 9, "bold")).pack(anchor="w", pady=(4, 10))
        card = tk.Frame(rail, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        card.pack(fill="x")
        card.columnconfigure(0, weight=1, uniform="pattern-column")
        card.columnconfigure(1, weight=1, uniform="pattern-column")
        tk.Label(card, text="Families", bg=PANEL, fg=INK, font=("TkDefaultFont", 9, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(11, 2))
        tk.Label(card, text="Drag one to change a class.", bg=PANEL, fg=MUTED, font=("TkDefaultFont", 8)).grid(row=1, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 4))
        self.family_blocks = {}
        for column, (family, label) in enumerate(FAMILY_CHOICES.items()):
            block = tk.Label(card, text=label, bg="#eef3ef", fg=GREEN_DARK, font=("TkDefaultFont", 8, "bold"), padx=4, pady=5, cursor="hand2", anchor="center")
            block.grid(row=2, column=column % 2, columnspan=1, sticky="ew", padx=4, pady=2)
            if column == 2:
                block.grid_configure(row=3, column=0, columnspan=2)
            self.family_blocks[family] = block
            HoverTip(block, FAMILY_DESCRIPTIONS[family] + " Drag this family onto Class A or B.")
            block.bind("<ButtonPress-1>", lambda e, f=family: self._drag_start_family(e, f))
            block.bind("<B1-Motion>", self._drag_motion)
            block.bind("<ButtonRelease-1>", self._drag_end)
            block.bind("<Double-Button-1>", lambda _e, f=family: self._quick_family(f))

        self.palette_mode_var = tk.StringVar(value="avoid")
        tk.Label(card, text="Pattern rule", bg=PANEL, fg=INK, font=("TkDefaultFont", 9, "bold")).grid(row=4, column=0, columnspan=2, sticky="w", padx=12, pady=(9, 2))
        mode_row = tk.Frame(card, bg="#eef3ef", padx=2, pady=2)
        mode_row.grid(row=5, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 4))
        self.mode_buttons = {}
        for mode in ("avoid", "contain"):
            button = tk.Button(mode_row, text=mode.title(), command=lambda m=mode: self._set_palette_mode(m), relief="flat", bd=0, cursor="hand2", font=("TkDefaultFont", 8, "bold"), padx=8, pady=4)
            button.pack(side="left", fill="x", expand=True)
            self.mode_buttons[mode] = button
            HoverTip(button, "Keep words with no occurrence of each dropped pattern." if mode == "avoid" else "Keep words that contain each dropped pattern.")
        self.pattern_blocks = {}
        for index, pattern in enumerate(PATTERNS):
            row, column = 6 + index // 2, index % 2
            block = tk.Label(card, text=f"⟨{pattern}⟩", bg="#fff0e9", fg="#965233", font=("TkDefaultFont", 9, "bold"), padx=5, pady=5, cursor="hand2", anchor="center")
            block.grid(row=row, column=column, sticky="ew", padx=4, pady=2)
            self.pattern_blocks[("avoid", pattern)] = block
            self.pattern_blocks[("contain", pattern)] = block
            HoverTip(block, lambda p=pattern: f"Drag to a class to {self.palette_mode_var.get()} pattern {p}. A pattern occurs when a subsequence has the same relative order. Double-click to add to the last focused class.")
            block.bind("<ButtonPress-1>", lambda e, p=pattern: self._drag_start(e, self.palette_mode_var.get(), p))
            block.bind("<B1-Motion>", self._drag_motion)
            block.bind("<ButtonRelease-1>", self._drag_end)
            block.bind("<Double-Button-1>", lambda _e, p=pattern: self._quick_add(self.palette_mode_var.get(), p))
        self._set_palette_mode("avoid")
        custom_row = 10
        tk.Label(card, text="CUSTOM PATTERN", bg=PANEL, fg=INK, font=("TkDefaultFont", 8, "bold")).grid(row=custom_row, column=0, columnspan=2, sticky="w", padx=12, pady=(10, 3))
        custom = tk.Frame(card, bg=PANEL)
        custom.grid(row=custom_row + 1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 3))
        custom.columnconfigure(0, weight=1)
        self.custom_pattern_var = tk.StringVar()
        pattern_entry = ttk.Entry(custom, textvariable=self.custom_pattern_var, width=12)
        pattern_entry.grid(row=0, column=0, columnspan=2, sticky="ew", padx=(0, 5), pady=(0, 4))
        HoverTip(pattern_entry, "Enter a standard pattern using digits, such as 3121. The selected Avoid/Contain rule will be used.")
        self.custom_target_var = tk.StringVar(value="Class A")
        self.custom_target_box = ttk.Combobox(custom, textvariable=self.custom_target_var, state="readonly", values=("Class A", "Class B"), width=8)
        self.custom_target_box.grid(row=1, column=0, sticky="ew", padx=(0, 5))
        HoverTip(self.custom_target_box, "Choose which class receives the custom pattern rule.")
        tk.Button(custom, text="Add rule", command=self.add_custom_rule, relief="flat", bg=GREEN, fg="white", activebackground=GREEN_DARK, cursor="hand2", font=("TkDefaultFont", 8, "bold"), padx=7, pady=5).grid(row=1, column=1, sticky="ew")
        self.custom_pattern_status = tk.Label(card, text="e.g. 3121  ·  double-click to add", bg=PANEL, fg=MUTED, font=("TkDefaultFont", 8), anchor="w")
        self.custom_pattern_status.grid(row=12, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 10))
        saved = tk.Frame(rail, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        saved.pack(fill="x", pady=(10, 0))
        top = tk.Frame(saved, bg=PANEL)
        top.pack(fill="x", padx=9, pady=7)
        self.saved_toggle = tk.Button(top, text="Saved tests  ·  0  ▸", command=self.toggle_saved, relief="flat", bg=PANEL, fg=INK, activebackground=PANEL, cursor="hand2", font=("TkDefaultFont", 8, "bold"))
        self.saved_toggle.pack(side="left")
        tk.Button(top, text="Save", command=self.save_current, relief="flat", bg=PANEL, fg=GREEN, activebackground=PANEL, cursor="hand2", font=("TkDefaultFont", 8, "bold")).pack(side="right")
        self.saved_content = tk.Frame(saved, bg=PANEL)
        self.saved_list = tk.Listbox(self.saved_content, height=4, relief="flat", borderwidth=0, highlightthickness=0, activestyle="none", bg=PANEL, fg=INK, selectbackground=MINT, selectforeground=INK, font=("TkDefaultFont", 9))
        self.saved_empty = tk.Label(self.saved_content, text="No saved tests yet. Save a test to keep it here.", bg=PANEL, fg=MUTED, font=("TkDefaultFont", 8), justify="left", anchor="w", padx=10, pady=6)
        self.saved_list.bind("<Double-Button-1>", self.load_saved)
        self.saved_open = False
        self._render_saved()
        actions = tk.Frame(self.saved_content, bg=PANEL)
        actions.pack(fill="x", padx=10, pady=(0, 8))
        tk.Button(actions, text="Export", command=self.export_state, relief="flat", bg="#f0f4f1", fg=INK, activebackground=MINT, cursor="hand2", font=("TkDefaultFont", 9), padx=9, pady=5).pack(side="left")
        tk.Button(actions, text="Import", command=self.import_state, relief="flat", bg="#f0f4f1", fg=INK, activebackground=MINT, cursor="hand2", font=("TkDefaultFont", 9), padx=9, pady=5).pack(side="left", padx=6)
        return rail

    def _build_workspace(self, parent):
        work = tk.Frame(parent, bg=BG)
        work.grid(row=0, column=1, sticky="nsew")
        work.columnconfigure(0, weight=1)
        work.rowconfigure(2, weight=1)
        intro = tk.Frame(work, bg=BG)
        intro.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        tk.Label(intro, text="Test a conjecture", bg=BG, fg=INK, font=("TkDefaultFont", 20 if self.compact_layout else 22, "bold")).pack(anchor="w")
        if not self.compact_layout:
            tk.Label(intro, text="Build a class comparison, check a finite range, and follow the first divergence.", bg=BG, fg=MUTED, font=("TkDefaultFont", 10)).pack(anchor="w", pady=(4, 0))

        composer = tk.Frame(work, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        composer.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        composer.columnconfigure(0, weight=1)
        composer_top = tk.Frame(composer, bg=PANEL)
        composer_top.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 4))
        tk.Label(composer_top, text="CONJECTURE COMPOSER", bg=PANEL, fg=MUTED, font=("TkDefaultFont", 9, "bold")).pack(side="left", padx=4, pady=(5, 4))
        tk.Button(composer_top, text="Load 2122 ↔ 2212 example", command=self.load_example, relief="flat", bg="#f0f4f1", fg=GREEN_DARK, activebackground=MINT, cursor="hand2", font=("TkDefaultFont", 8, "bold"), padx=9, pady=5).pack(side="right")
        sides = tk.Frame(composer, bg=PANEL)
        sides.grid(row=1, column=0, sticky="ew", padx=12)
        sides.columnconfigure(0, weight=1, uniform="side")
        sides.columnconfigure(2, weight=1, uniform="side")
        sides.columnconfigure(1, weight=0)
        self.left_lane = DropLane(sides, self, "left")
        self.left_lane.grid(row=0, column=0, sticky="nsew")
        center = tk.Frame(sides, bg=PANEL, width=56)
        center.grid(row=0, column=1, sticky="ns")
        tk.Label(center, text="VS", bg=PANEL, fg=MUTED, font=("TkDefaultFont", 9, "bold")).place(relx=.5, rely=.5, anchor="center")
        self.right_lane = DropLane(sides, self, "right")
        self.right_lane.grid(row=0, column=2, sticky="nsew")
        question = tk.Frame(composer, bg=PANEL)
        question.grid(row=2, column=0, sticky="ew", padx=16, pady=(12, 14))
        tk.Label(question, text="Compare through n", bg=PANEL, fg=MUTED, font=("TkDefaultFont", 9)).pack(side="left")
        self.start_var = tk.StringVar(value="1")
        self.stop_var = tk.StringVar(value="8")
        self.start_box = ttk.Spinbox(question, from_=1, to=11, width=4, textvariable=self.start_var, command=self.changed)
        self.start_box.pack(side="left", padx=(8, 5))
        HoverTip(self.start_box, "First degree to test. For example, start at 3 to skip degrees 1 and 2.")
        tk.Label(question, text="to", bg=PANEL, fg=MUTED).pack(side="left")
        self.stop_box = ttk.Spinbox(question, from_=1, to=11, width=4, textvariable=self.stop_var, command=self.changed)
        self.stop_box.pack(side="left", padx=(5, 14))
        HoverTip(self.stop_box, "Last degree included in this finite test. The family limits the maximum available degree.")
        tk.Label(question, text="Refine counts by", bg=PANEL, fg=MUTED, font=("TkDefaultFont", 9)).pack(side="left", padx=(5, 7))
        self.stat_var = tk.StringVar(value=STATISTICS["none"])
        self.stat_box = ttk.Combobox(question, state="readonly", width=27, textvariable=self.stat_var, values=list(STATISTICS.values()))
        self.stat_box.pack(side="left")
        self.stat_box.bind("<<ComboboxSelected>>", lambda _e: self.changed())
        HoverTip(self.stat_box, lambda: STAT_DESCRIPTIONS.get(self._stat_key(), "Choose a statistic to compare its distribution as well as the total."))
        self.start_var.trace_add("write", lambda *_: self.changed())
        self.stop_var.trace_add("write", lambda *_: self.changed())
        self.question_text = tk.Label(composer, text="", bg=MINT, fg=GREEN_DARK, font=("TkDefaultFont", 10), justify="left", anchor="w", padx=14, pady=10, wraplength=1000)
        self.question_text.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))
        self.question_text.bind("<Configure>", lambda event: self.question_text.configure(wraplength=max(320, event.width - 28)))

        results = tk.Frame(work, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        results.grid(row=2, column=0, sticky="nsew")
        results.rowconfigure(2, weight=1)
        results.columnconfigure(0, weight=1)
        result_top = tk.Frame(results, bg=PANEL)
        result_top.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        result_top.columnconfigure(0, weight=1)
        self.result_headline = tk.Label(result_top, text="Ready when you are", bg=PANEL, fg=INK, font=("TkDefaultFont", 16, "bold"))
        self.result_headline.grid(row=0, column=0, sticky="w")
        self.run_button = tk.Button(result_top, text="▶   Run bounded test", command=self.run, relief="flat", bg=GREEN, fg="white", activebackground=GREEN_DARK, activeforeground="white", cursor="hand2", font=("TkDefaultFont", 10, "bold"), padx=15, pady=10)
        self.run_button.grid(row=0, column=1, rowspan=2, sticky="e")
        self.result_subtitle = tk.Label(result_top, text="Matching finite counts are evidence through n, not a proof for all degrees.", bg=PANEL, fg=MUTED, font=("TkDefaultFont", 9))
        self.result_subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.progress = ttk.Progressbar(results, mode="indeterminate", style="Horizontal.TProgressbar")
        self.progress.grid(row=1, column=0, sticky="ew", padx=16, pady=(4, 9))
        self.progress.grid_remove()
        columns = ("n", "left", "right", "difference", "status")
        table_frame = tk.Frame(results, bg=PANEL)
        table_frame.grid(row=2, column=0, sticky="nsew", padx=15, pady=(0, 8))
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        for key, title, width, anchor in (("n", "DEGREE n", 95, "center"), ("left", "CLASS A", 160, "e"), ("right", "CLASS B", 160, "e"), ("difference", "A − B", 145, "e"), ("status", "RESULT", 180, "w")):
            self.table.heading(key, text=title)
            self.table.column(key, width=width, anchor=anchor, stretch=key == "status")
        self.table.grid(row=0, column=0, sticky="nsew")
        table_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        table_scrollbar.grid(row=0, column=1, sticky="ns")
        self.table.configure(yscrollcommand=table_scrollbar.set)
        self.table.tag_configure("match", foreground=GREEN_DARK)
        self.table.tag_configure("diverge", foreground=RED, background="#fff6f4")
        self.footer = tk.Label(results, text="Choose patterns from the left, then drop them into either class.", bg="#f8faf8", fg=MUTED, anchor="w", padx=14, pady=9, font=("TkDefaultFont", 9))
        self.footer.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))
        return work

    def _quick_add(self, mode, pattern):
        """Accessible alternative to dragging: double-click adds to focused lane."""
        side = getattr(self, "focused_side", "left")
        self.add_rule(side, mode, pattern)

    def _set_palette_mode(self, mode):
        self.palette_mode_var.set(mode)
        for key, button in self.mode_buttons.items():
            active = key == mode
            button.configure(bg=GREEN if active else "#eef3ef", fg="white" if active else INK, activebackground=GREEN if active else MINT)
        color, foreground = ("#fff0e9", "#965233") if mode == "avoid" else (MINT, GREEN_DARK)
        for pattern in PATTERNS:
            block = self.pattern_blocks[(mode, pattern)]
            block.configure(bg=color, fg=foreground)

    def _quick_family(self, family):
        side = getattr(self, "focused_side", "left")
        self.set_family(side, family)

    def set_family(self, side, family):
        lane = self.left_lane if side == "left" else self.right_lane
        lane.family.set(FAMILY_CHOICES[family])
        self.changed()
        if hasattr(self, "footer"):
            self.footer.configure(text=f"{FAMILY_CHOICES[family]} family set for Class {'A' if side == 'left' else 'B'}.", fg=GREEN_DARK)

    def _show_view(self, view):
        if view == "conjecture":
            self.transform_view.grid_remove()
            self.main_rail.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
            self.main_work.grid(row=0, column=1, sticky="nsew")
        else:
            self.main_rail.grid_remove()
            self.main_work.grid_remove()
            self.transform_view.grid(row=0, column=0, columnspan=2, sticky="nsew")
        for key, button in self.nav_buttons.items():
            selected = key == view
            button.configure(bg=GREEN if selected else "#e8eeea", fg="white" if selected else INK, activebackground=GREEN if selected else MINT)

    def _build_transform_view(self, parent):
        view = tk.Frame(parent, bg=BG)
        view.grid(row=0, column=0, columnspan=2, sticky="nsew")
        view.columnconfigure(0, weight=1)
        view.rowconfigure(2, weight=1)
        intro = tk.Frame(view, bg=BG)
        intro.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        tk.Label(intro, text="See what a transform does", bg=BG, fg=INK, font=("TkDefaultFont", 21, "bold")).pack(anchor="w")
        tk.Label(intro, text="Apply one engine transformation to a word. Compare positions, values, and the exact mapping.", bg=BG, fg=MUTED, font=("TkDefaultFont", 10)).pack(anchor="w", pady=(4, 0))

        controls = tk.Frame(view, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        controls.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        controls.columnconfigure(1, weight=1)
        controls.columnconfigure(3, weight=1)
        tk.Label(controls, text="SOURCE WORD", bg=PANEL, fg=MUTED, font=("TkDefaultFont", 8, "bold")).grid(row=0, column=0, sticky="w", padx=(14, 6), pady=(12, 4))
        self.transform_word_var = tk.StringVar(value="1 2 1 3 2")
        self.transform_word_entry = ttk.Entry(controls, textvariable=self.transform_word_var, width=24)
        self.transform_word_entry.grid(row=0, column=1, sticky="ew", padx=(0, 14), pady=(12, 4))
        HoverTip(self.transform_word_entry, "Enter positive values separated by spaces or commas. Example: 1 2 1 3 2.")
        tk.Label(controls, text="TRANSFORMATION", bg=PANEL, fg=MUTED, font=("TkDefaultFont", 8, "bold")).grid(row=0, column=2, sticky="w", padx=(0, 6), pady=(12, 4))
        self.transform_labels = {
            "Reverse positions": "reverse", "Complement values": "complement",
            "Hat map": "hat", "Inverse hat map": "inverse_hat",
            "Prefix lift Lᵢ": "prefix_lift", "Inverse prefix lift Lᵢ": "inverse_prefix_lift",
            "Insert position": "insert_position", "Delete position": "delete_position",
        }
        names = tuple(self.transform_labels)
        self.transform_name_var = tk.StringVar(value="prefix_lift")
        self.transform_name_var.set("Prefix lift Lᵢ")
        self.transform_name_box = ttk.Combobox(controls, state="readonly", width=21, textvariable=self.transform_name_var, values=names)
        self.transform_name_box.grid(row=0, column=3, sticky="w", padx=(0, 14), pady=(12, 4))
        self.transform_name_box.bind("<<ComboboxSelected>>", lambda _e: self._transform_parameter_state())
        HoverTip(self.transform_name_box, lambda: TRANSFORM_DESCRIPTIONS.get(self.transform_labels.get(self.transform_name_var.get(), ""), "Choose a map to see what it does."))
        self.transform_parameter_label = tk.Label(controls, text="POSITION", bg=PANEL, fg=MUTED, font=("TkDefaultFont", 8, "bold"))
        self.transform_parameter_label.grid(row=1, column=0, sticky="w", padx=(14, 6), pady=(4, 11))
        self.transform_parameter_var = tk.StringVar(value="3")
        self.transform_parameter_entry = ttk.Entry(controls, textvariable=self.transform_parameter_var, width=6)
        self.transform_parameter_entry.grid(row=1, column=1, sticky="w", padx=(0, 14), pady=(4, 11))
        HoverTip(self.transform_parameter_entry, lambda: "Positions are 1-based; for insertion, cuts are 0 through the word length. Click a position on the Before graph to fill this field.")
        self.transform_value_label = tk.Label(controls, text="INSERT VALUE", bg=PANEL, fg=MUTED, font=("TkDefaultFont", 8, "bold"))
        self.transform_value_label.grid(row=1, column=2, sticky="w", padx=(0, 6), pady=(4, 11))
        self.transform_value_var = tk.StringVar(value="2")
        self.transform_value_entry = ttk.Entry(controls, textvariable=self.transform_value_var, width=6)
        self.transform_value_entry.grid(row=1, column=3, sticky="w", padx=(0, 14), pady=(4, 11))
        HoverTip(self.transform_value_entry, "Insert an existing value level from the source word; for example, insert value 2.")
        tk.Button(controls, text="Apply transform", command=self.apply_transform, relief="flat", bg=GREEN, fg="white", activebackground=GREEN_DARK, activeforeground="white", cursor="hand2", font=("TkDefaultFont", 9, "bold"), padx=12, pady=7).grid(row=1, column=8, sticky="e", padx=(0, 14), pady=(3, 10))
        self.transform_help = tk.Label(controls, text="Use spaces or commas between values. Positions and cuts are 1-based, except insertion cut 0 (before the first position).", bg=PANEL, fg=MUTED, font=("TkDefaultFont", 9), anchor="w")
        self.transform_help.grid(row=2, column=0, columnspan=9, sticky="ew", padx=14, pady=(0, 11))

        stage = tk.Frame(view, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        stage.grid(row=2, column=0, sticky="nsew")
        stage.columnconfigure(0, weight=1, uniform="stage")
        stage.columnconfigure(1, weight=1, uniform="stage")
        stage.rowconfigure(1, weight=1)
        tk.Label(stage, text="BEFORE", bg=PANEL, fg=MUTED, font=("TkDefaultFont", 9, "bold")).grid(row=0, column=0, sticky="w", padx=16, pady=(13, 3))
        tk.Label(stage, text="AFTER", bg=PANEL, fg=MUTED, font=("TkDefaultFont", 9, "bold")).grid(row=0, column=1, sticky="w", padx=16, pady=(13, 3))
        self.before_canvas = tk.Canvas(stage, bg="#fbfcfb", height=250, highlightthickness=0)
        self.before_canvas.grid(row=1, column=0, sticky="nsew", padx=(12, 6), pady=(0, 10))
        self.after_canvas = tk.Canvas(stage, bg="#fbfcfb", height=250, highlightthickness=0)
        self.after_canvas.grid(row=1, column=1, sticky="nsew", padx=(6, 12), pady=(0, 10))
        self.transform_summary = tk.Label(stage, text="Choose a word and transform, then apply it to see the mapping.", bg=MINT, fg=GREEN_DARK, font=("TkDefaultFont", 10), anchor="w", justify="left", padx=14, pady=10, wraplength=1150)
        self.transform_summary.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 8))
        self.transform_mapping = tk.Label(stage, text="", bg=PANEL, fg=INK, font=("TkFixedFont", 10), anchor="w", justify="left", padx=16, pady=8, wraplength=1150)
        self.transform_mapping.grid(row=3, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 10))
        view.bind("<Configure>", lambda _e: self._redraw_transform() if getattr(self, "_last_transform", None) else None)
        self._transform_parameter_state()
        return view

    def _transform_parameter_state(self):
        name = self.transform_labels.get(self.transform_name_var.get(), self.transform_name_var.get())
        uses_param = name in {"prefix_lift", "inverse_prefix_lift", "insert_position", "delete_position"}
        self.transform_parameter_label.configure(text="CUT" if name == "insert_position" else "POSITION")
        if uses_param:
            self.transform_parameter_label.grid()
            self.transform_parameter_entry.grid()
        else:
            self.transform_parameter_label.grid_remove()
            self.transform_parameter_entry.grid_remove()
        if name == "insert_position":
            self.transform_value_label.grid()
            self.transform_value_entry.grid()
        else:
            self.transform_value_label.grid_remove()
            self.transform_value_entry.grid_remove()
        guidance = TRANSFORM_DESCRIPTIONS.get(name, "Choose a transform to see what changes.")
        if uses_param:
            guidance += " Click a position in the Before graph to choose the pivot, cut, or position to remove."
        self.transform_help.configure(text=guidance)

    def _parse_visual_word(self):
        text = self.transform_word_var.get().strip()
        if not text:
            raise ValueError("Enter a nonempty word using positive values, such as 1 2 1 3.")
        values = tuple(int(v) for v in text.replace(",", " ").replace(";", " ").split())
        if any(v < 1 for v in values):
            raise ValueError("Values must be positive integers.")
        return ChainWord(values)

    def apply_transform(self):
        try:
            source = self._parse_visual_word()
            name = self.transform_labels.get(self.transform_name_var.get(), self.transform_name_var.get())
            parameter = int(self.transform_parameter_var.get()) if name in {"prefix_lift", "inverse_prefix_lift", "insert_position", "delete_position"} else None
            if name == "reverse":
                result = reverse(source); detail = "Reverse the order of positions."
            elif name == "complement":
                result = complement(source); detail = f"Replace each value v by height + 1 − v (height {source.height})."
            elif name == "hat":
                output = hat(source); result = None; detail = "Apply the ordered prefix lifts at the source word’s ascent-top positions."
            elif name == "inverse_hat":
                output = inverse_hat(source); result = None; detail = "Undo the hat map using the preserved ascent-top positions; this is partial."
            elif name == "prefix_lift":
                result = prefix_lift(source, parameter); detail = f"At pivot {parameter}, raise earlier values at least the pivot value {source.at(parameter)}."
            elif name == "inverse_prefix_lift":
                result = inverse_prefix_lift(source, parameter); detail = f"At first-occurrence pivot {parameter}, lower earlier values above the pivot value {source.at(parameter)}."
            elif name == "insert_position":
                value = int(self.transform_value_var.get())
                result = insert_position(source, parameter, value); detail = f"Insert value {value} after cut {parameter}; later positions shift right."
            elif name == "delete_position":
                if not 1 <= parameter <= len(source):
                    raise ValueError("Position to delete must be within the word.")
                result = restrict_positions(source, [i for i in range(1, len(source) + 1) if i != parameter]); detail = f"Delete position {parameter}; later positions shift left."
            else:
                raise ValueError("Choose a supported transform.")
            if result is not None:
                output, position_map, value_map, created = result.output, result.position_map, result.value_map, result.created_positions
            else:
                position_map, value_map, created = tuple(range(1, len(source) + 1)), None, ()
            self._last_transform = (source, output, name, detail, position_map, value_map, created)
            self._redraw_transform()
        except (ValueError, IndexError, TypeError) as exc:
            self.transform_summary.configure(text=f"Cannot apply transform: {exc}", bg="#fff0ed", fg=RED)

    def _redraw_transform(self):
        if not getattr(self, "_last_transform", None):
            return
        if getattr(self, "_drawing_transform", False):
            return
        self._drawing_transform = True
        try:
            self._draw_transform_contents()
        finally:
            self._drawing_transform = False

    def _draw_transform_contents(self):
        source, output, name, detail, pmap, vmap, created = self._last_transform
        self._draw_sequence(self.before_canvas, source, set(), selectable=True)
        old_by_id = {pid: value for pid, value in zip(source.position_ids, source.values)}
        changed_after = {i for i, (pid, value) in enumerate(zip(output.position_ids, output.values), start=1) if pid not in old_by_id or old_by_id[pid] != value}
        self._draw_sequence(self.after_canvas, output, changed_after)
        pmap_text = "position map: " + ", ".join(f"{i}→{j if j is not None else 'deleted'}" for i, j in enumerate(pmap, start=1))
        if vmap is None and name in {"prefix_lift", "inverse_prefix_lift"}:
            value_map_label = "position-dependent; inspect the before/after values"
        elif vmap is None:
            value_map_label = "not supplied by this transform"
        else:
            value_map_label = ", ".join(f"{i}→{j if j is not None else 'deleted'}" for i, j in enumerate(vmap, start=1))
        vmap_text = "value map: " + value_map_label
        self.transform_summary.configure(text=f"{name.replace('_', ' ').title()} · {detail}   Result: {list(output.values)} (length {len(output)}, height {output.height}). Amber marks changed or newly inserted entries.", bg=MINT, fg=GREEN_DARK)
        self.transform_mapping.configure(text=f"{pmap_text}\n{vmap_text}" + (f"\nNew positions: {', '.join(map(str, created))}" if created else ""))

    def _draw_sequence(self, canvas, word, created, selectable=False):
        canvas.delete("all")
        width = max(canvas.winfo_width(), 320)
        height = max(canvas.winfo_height(), 210)
        left, right, top, bottom = 42, width - 30, 24, height - 38
        max_value = max(word.height, 1)
        xstep = (right - left) / max(len(word) - 1, 1)
        ystep = (bottom - top) / max(max_value - 1, 1)
        points = []
        for level in range(1, max_value + 1):
            y = bottom - (level - 1) * ystep if max_value > 1 else (top + bottom) / 2
            canvas.create_line(left - 10, y, right + 4, y, fill="#e8eeea", dash=(2, 4))
            canvas.create_text(left - 17, y, text=str(level), anchor="e", fill=MUTED, font=("TkDefaultFont", 8))
        for index, value in enumerate(word.values):
            x = left + index * xstep if len(word) > 1 else (left + right) / 2
            y = bottom - (value - 1) * ystep if max_value > 1 else (top + bottom) / 2
            points.append((x, y))
        for index in range(len(points) - 1):
            x1, y1 = points[index]; x2, y2 = points[index + 1]
            color = GREEN if word.values[index] < word.values[index + 1] else ("#bb7951" if word.values[index] > word.values[index + 1] else "#9aa69f")
            canvas.create_line(x1, y1, x2, y2, fill=color, width=2, arrow="last", arrowshape=(7, 8, 3))
        for index, ((x, y), value) in enumerate(zip(points, word.values), start=1):
            fill = AMBER if index in created else GREEN
            tags = (f"position-{index}",) if selectable else ()
            oval = canvas.create_oval(x - 14, y - 14, x + 14, y + 14, fill=fill, outline="white", width=2, tags=tags)
            text_id = canvas.create_text(x, y, text=str(value), fill="white", font=("TkDefaultFont", 10, "bold"), tags=tags)
            if selectable:
                for item in (oval, text_id):
                    canvas.tag_bind(item, "<Enter>", lambda _e: canvas.configure(cursor="hand2"))
                    canvas.tag_bind(item, "<Leave>", lambda _e: canvas.configure(cursor=""))
                    canvas.tag_bind(item, "<Button-1>", lambda _e, position=index: self._select_visual_position(position))
            canvas.create_text(x, bottom + 23, text=f"{index}", fill=MUTED, font=("TkDefaultFont", 9))
        if not word.values:
            canvas.create_text(width / 2, height / 2, text="empty word", fill=MUTED, font=("TkDefaultFont", 10, "italic"))
        canvas.create_text(12, 13, text="value level ↑", anchor="w", fill=MUTED, font=("TkDefaultFont", 8))

    def _select_visual_position(self, position):
        name = self.transform_labels.get(self.transform_name_var.get(), "")
        if name not in {"prefix_lift", "inverse_prefix_lift", "insert_position", "delete_position"}:
            return
        # A position click chooses the pivot/deletion position, or the cut after
        # that position for insertion. Cut 0 remains available in the field.
        self.transform_parameter_var.set(str(position))
        self.apply_transform()

    def _drag_start(self, event, mode, pattern):
        self.drag_payload = {"kind": "pattern", "mode": mode, "pattern": pattern}
        event.widget.configure(relief="sunken")

    def _drag_start_family(self, event, family):
        self.drag_payload = {"kind": "family", "family": family}
        event.widget.configure(relief="sunken")

    def _drag_motion(self, event):
        if not self.drag_payload:
            return
        x, y = self.root.winfo_pointerx(), self.root.winfo_pointery()
        target = self.root.winfo_containing(x, y)
        for side, lane in (("left", self.left_lane), ("right", self.right_lane)):
            lane._highlight(lane._contains(target))

    def _drag_end(self, event):
        if self.drag_payload:
            x, y = self.root.winfo_pointerx(), self.root.winfo_pointery()
            target = self.root.winfo_containing(x, y)
            for side, lane in (("left", self.left_lane), ("right", self.right_lane)):
                lane._highlight(False)
                if lane._contains(target):
                    if self.drag_payload["kind"] == "family":
                        self.set_family(side, self.drag_payload["family"])
                    else:
                        self.add_rule(side, self.drag_payload["mode"], self.drag_payload["pattern"])
                    break
        event.widget.configure(relief="flat")
        self.drag_payload = None

    def add_rule(self, side, mode, pattern):
        values = [int(x) for x in pattern]
        rule = {"mode": mode, "pattern": values}
        if rule not in self.rules[side]:
            self.rules[side].append(rule)
            self.left_lane.render(); self.right_lane.render(); self.changed()

    def add_custom_rule(self):
        try:
            pattern = ClassicalPattern(self.custom_pattern_var.get()).values
        except (TypeError, ValueError) as exc:
            self.custom_pattern_status.configure(text=f"Check pattern: {exc}", fg=RED)
            return
        side = "left" if self.custom_target_var.get() == "Class A" else "right"
        mode = self.palette_mode_var.get()
        self.add_rule(side, mode, pattern)
        self.custom_pattern_status.configure(text=f"Added {mode} ⟨{', '.join(map(str, pattern))}⟩ to {self.custom_target_var.get()}.", fg=GREEN_DARK)
        self.custom_pattern_var.set("")

    def load_example(self):
        self.left_lane.family.set(FAMILY_CHOICES["modified"])
        self.right_lane.family.set(FAMILY_CHOICES["modified"])
        self.rules["left"] = [{"mode": "avoid", "pattern": [2, 1, 2, 2]}]
        self.rules["right"] = [{"mode": "avoid", "pattern": [2, 2, 1, 2]}]
        self.start_var.set("1")
        self.stop_var.set("9")
        self.stat_var.set(STATISTICS["none"])
        self._set_palette_mode("avoid")
        self.left_lane.render()
        self.right_lane.render()
        self.changed()
        self.footer.configure(text="Example loaded: compare Modified 2122-avoiders with Modified 2212-avoiders through degree 9.", fg=GREEN_DARK)

    def remove_rule(self, side, index):
        del self.rules[side][index]
        self.left_lane.render(); self.right_lane.render(); self.changed()

    def _display_family(self, family):
        return FAMILY_LABELS.get(family, family.title())

    def family_description(self, value):
        return FAMILY_DESCRIPTIONS.get(_family_key(value), "Choose a sequence family.")

    def _refresh_conjecture(self):
        try:
            start, stop = int(self.start_var.get()), int(self.stop_var.get())
        except ValueError:
            start, stop = 1, 8
        def describe(side):
            lane = self.left_lane if side == "left" else self.right_lane
            family = self._display_family(_family_key(lane.family.get()))
            rules = self.rules[side]
            if not rules:
                return f"all {family} ascent sequences"
            parts = [f"{r['mode']} ⟨{', '.join(map(str, r['pattern']))}⟩" for r in rules]
            return f"{family} ascent sequences that " + " and ".join(parts)
        stat = self._stat_key()
        suffix = " by total count" if stat == "none" else f" by {STATISTICS.get(stat, stat)} distribution"
        if stop >= start:
            self.question_text.configure(text=f"Test whether {describe('left')} and {describe('right')} have equal counts{suffix} for every n = {start}, …, {stop}.")

    def changed(self):
        if hasattr(self, "left_lane"):
            self._refresh_conjecture()
            if self._save_timer:
                self.root.after_cancel(self._save_timer)
            self._save_timer = self.root.after(500, self._autosave)

    def _spec(self):
        try:
            start, stop = int(self.start_var.get()), int(self.stop_var.get())
        except ValueError as exc:
            raise ValueError("Enter whole-number degree bounds.") from exc
        if not 1 <= start <= stop <= 11:
            raise ValueError("Choose 1 ≤ start ≤ stop ≤ 11.")
        left_family, right_family = _family_key(self.left_lane.family.get()), _family_key(self.right_lane.family.get())
        for label, family in (("Class A", left_family), ("Class B", right_family)):
            if stop > FAMILY_LIMITS[family]:
                raise ValueError(f"{label} generation is bounded to degree {FAMILY_LIMITS[family]} for {family} sequences.")
        return {"question": "compare", "start": start, "stop": stop, "statistic": self._stat_key(), "left": _side(left_family, self.rules["left"]), "right": _side(right_family, self.rules["right"])}

    def _stat_key(self):
        return next((key for key, label in STATISTICS.items() if label == self.stat_var.get()), "none")

    def run(self):
        if self.run_button["state"] == "disabled":
            return
        try:
            spec = self._spec()
        except ValueError as exc:
            messagebox.showerror("Check the experiment", str(exc), parent=self.root)
            return
        self.run_button.configure(state="disabled", text="Testing…")
        self.header_status.configure(text="COMPUTING LOCALLY")
        self.progress.grid()
        self.progress.start(12)
        self.result_headline.configure(text="Enumerating sequences…")
        self.footer.configure(text="The exact engine is running in the background. You can keep the experiment window open.")
        threading.Thread(target=self._run_worker, args=(spec,), daemon=True).start()

    def _run_worker(self, spec):
        try:
            result = run_experiment(spec)
            self._worker_messages.put(("ok", spec, result))
        except Exception as exc:
            self._worker_messages.put(("error", str(exc), None))

    def _poll_worker(self):
        try:
            while True:
                kind, first, result = self._worker_messages.get_nowait()
                self.progress.stop()
                self.progress.grid_remove()
                self.run_button.configure(state="normal", text="▶   Run bounded test")
                self.header_status.configure(text="LOCAL · FINITE TESTS")
                if kind == "error":
                    self.result_headline.configure(text="Test could not run")
                    self.footer.configure(text=first)
                    continue
                self.saved_result = result
                self._show_result(result)
                self._autosave()
        except queue.Empty:
            pass
        self.root.after(120, self._poll_worker)

    def _show_result(self, result):
        for row in self.table.get_children():
            self.table.delete(row)
        for row in result["rows"]:
            left, right = row["left_count"], row["right_count"]
            difference = row["difference"]
            matches = row["counts_match"]
            stat_match = row.get("distributions_match", True)
            status = ("COUNT + STAT MATCH" if stat_match else "STATISTIC DIVERGENCE") if matches and result["statistic"] != "none" else ("MATCH" if matches else "DIVERGENCE")
            tag = "match" if matches and stat_match else "diverge"
            self.table.insert("", "end", values=(row["n"], f"{left:,}", f"{right:,}", f"{difference:+,}", status), tags=(tag,))
        self.result_headline.configure(text=result["headline"], fg=GREEN_DARK if result["all_counts_match"] else (RED if result["first_divergence"] else INK))
        self.result_subtitle.configure(text=f"Tested {result['tested_objects']:,} generated objects in {result['runtime_seconds']:.3f}s · finite computation only")
        if result["first_divergence"]:
            n = result["first_divergence"]["n"]
            self.footer.configure(text=f"Counterexample degree: n={n}. This refutes equality of these finite counts at that degree.", fg=RED)
        elif result["all_counts_match"]:
            self.footer.configure(text=f"Counts agree for every tested degree from {result['specification']['start']} to {result['specification']['stop']}. This is finite evidence, not an all-degree proof.", fg=GREEN_DARK)
        else:
            self.footer.configure(text="Single-class count complete.", fg=MUTED)

    def _current_draft(self):
        return {"left_family": _family_key(self.left_lane.family.get()), "right_family": _family_key(self.right_lane.family.get()), "left_rules": json.dumps(self.rules["left"]), "right_rules": json.dumps(self.rules["right"]), "start": self.start_var.get(), "stop": self.stop_var.get(), "statistic": self._stat_key()}

    def _restore_draft(self):
        draft = self.state.get("draft", {})
        if not isinstance(draft, dict):
            return
        for side, lane in (("left", self.left_lane), ("right", self.right_lane)):
            family = draft.get(f"{side}_family")
            if family in FAMILIES:
                lane.family.set(FAMILY_CHOICES[family])
            rules = draft.get(f"{side}_rules", "[]")
            if isinstance(rules, str):
                try:
                    rules = json.loads(rules)
                except json.JSONDecodeError:
                    rules = []
            if isinstance(rules, list):
                self.rules[side] = [r for r in rules if isinstance(r, dict) and r.get("mode") in {"avoid", "contain"} and isinstance(r.get("pattern"), list)]
            lane.render()
        self.start_var.set(str(draft.get("start", "1")))
        self.stop_var.set(str(draft.get("stop", "8")))
        stat = draft.get("statistic", "none")
        self.stat_var.set(STATISTICS[stat] if stat in STATISTICS else STATISTICS["none"])

    def _autosave(self):
        self._save_timer = None
        self.state["draft"] = self._current_draft()
        try:
            write_state(self.state)
        except (ValueError, OSError):
            pass

    def _render_saved(self):
        if not hasattr(self, "saved_list"):
            return
        self.saved_list.delete(0, "end")
        saved = self.state.get("saved", [])
        for item in saved:
            self.saved_list.insert("end", item.get("name", "Saved conjecture"))
        self.saved_toggle.configure(text=f"Saved tests  ·  {len(saved)}  {'▾' if self.saved_open else '▸'}")
        self.saved_content.pack(fill="x", padx=4, pady=(0, 4)) if self.saved_open else self.saved_content.pack_forget()
        if saved:
            self.saved_empty.pack_forget()
            self.saved_list.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        else:
            self.saved_list.pack_forget()
            self.saved_empty.pack(fill="x", padx=8, pady=(0, 4))

    def toggle_saved(self):
        self.saved_open = not self.saved_open
        self._render_saved()

    def save_current(self):
        try:
            spec = self._spec()
        except ValueError as exc:
            messagebox.showerror("Check the experiment", str(exc), parent=self.root)
            return
        name = f"{self._display_family(spec['left']['family'])} vs {self._display_family(spec['right']['family'])} · n={spec['start']}–{spec['stop']}"
        saved = self.state.setdefault("saved", [])
        saved.insert(0, {"name": name, "specification": spec, "result": self.saved_result if self.saved_result and self.saved_result.get("specification") == spec else None})
        self.state["saved"] = saved[:30]
        self._autosave(); self._render_saved()

    def load_saved(self, _event=None):
        selection = self.saved_list.curselection()
        if not selection:
            return
        item = self.state.get("saved", [])[selection[0]]
        spec = item.get("specification", {})
        self.left_lane.family.set(FAMILY_CHOICES.get(spec.get("left", {}).get("family", "modified"), "Modified"))
        self.right_lane.family.set(FAMILY_CHOICES.get(spec.get("right", {}).get("family", "modified"), "Modified"))
        self.rules["left"] = spec.get("left", {}).get("rules", [])
        self.rules["right"] = spec.get("right", {}).get("rules", [])
        self.start_var.set(str(spec.get("start", 1))); self.stop_var.set(str(spec.get("stop", 8)))
        self.stat_var.set(STATISTICS.get(spec.get("statistic", "none"), STATISTICS["none"]))
        self.left_lane.render(); self.right_lane.render(); self.changed()
        if item.get("result"):
            self.saved_result = item["result"]
            self._show_result(self.saved_result)

    def export_state(self):
        path = filedialog.asksaveasfilename(parent=self.root, title="Export research tests", defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        self._autosave()
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(self.state, handle, indent=2, ensure_ascii=False)
        except OSError as exc:
            messagebox.showerror("Export failed", str(exc), parent=self.root)

    def import_state(self):
        path = filedialog.askopenfilename(parent=self.root, title="Import research tests", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as handle:
                loaded = write_state(json.load(handle))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            messagebox.showerror("Import failed", str(exc), parent=self.root)
            return
        self.state = loaded
        self._restore_draft(); self.left_lane.render(); self.right_lane.render(); self._render_saved(); self.changed()


def _startup_check() -> None:
    """Check frozen imports and a small engine run without opening a window."""
    from ac.gui.experiments import run_experiment
    from ac.gui.research_state import read_state

    assert isinstance(read_state(), dict)
    result = run_experiment({
        "question": "compare", "start": 1, "stop": 3, "statistic": "none",
        "left": {"family": "modified", "rules": [{"mode": "avoid", "pattern": [2, 1, 2, 2]}]},
        "right": {"family": "modified", "rules": [{"mode": "avoid", "pattern": [2, 2, 1, 2]}]},
    })
    if len(result["rows"]) != 3:
        raise RuntimeError("engine smoke test returned an incomplete degree range")
    _log("startup_check_passed", engine_rows=len(result["rows"]))


def _window_smoke_check() -> None:
    """Create and map the real desktop workbench, then close it automatically."""
    root = tk.Tk()
    app = DesktopWorkbench(root)
    root.update()
    if not root.winfo_ismapped():
        root.destroy()
        raise RuntimeError("native Tk window was not mapped")
    # Exercise the same press, hover, and release handlers used by a native drag.
    # The pointer target is controlled so the check is deterministic on each OS.
    block = app.pattern_blocks[("avoid", "2122")]
    drag_event = type("DragEvent", (), {"widget": block})()
    original_containing = root.winfo_containing
    try:
        app._drag_start(drag_event, "avoid", "2122")
        root.winfo_containing = lambda *_args: app.right_lane
        app._drag_motion(drag_event)
        if int(app.right_lane.cget("highlightthickness")) != 2:
            root.destroy()
            raise RuntimeError("dragging a preset did not highlight Class B")
        app._drag_end(drag_event)
    finally:
        root.winfo_containing = original_containing
    if {"mode": "avoid", "pattern": [2, 1, 2, 2]} not in app.rules["right"] or app.drag_payload is not None:
        root.destroy()
        raise RuntimeError("dragged preset did not land in Class B")
    app.focused_side = "left"
    app._quick_add("contain", "221")
    if {"mode": "contain", "pattern": [2, 2, 1]} not in app.rules["left"]:
        root.destroy()
        raise RuntimeError("double-click quick-add did not reach the focused class")
    try:
        app._drag_start_family(drag_event, "revised")
        root.winfo_containing = lambda *_args: app.left_lane
        app._drag_end(drag_event)
    finally:
        root.winfo_containing = original_containing
    if app.left_lane.family.get() != "Revised":
        root.destroy()
        raise RuntimeError("dragging a family did not update Class A")
    app.left_lane.family.set("Modified")
    app.stat_var.set(STATISTICS["ascent_runs"])
    if app._spec()["statistic"] != "ascent_runs":
        root.destroy()
        raise RuntimeError("human-readable statistic choice did not map to the engine")
    app.stat_var.set(STATISTICS["none"])
    app.custom_pattern_var.set("3121")
    app.add_custom_rule()
    if {"mode": "avoid", "pattern": [3, 1, 2, 1]} not in app.rules["left"]:
        root.destroy()
        raise RuntimeError("custom pattern rule did not reach Class A")
    app.load_example()
    app._show_view("transform")
    app.apply_transform()
    app._select_visual_position(2)
    root.update()
    if app.transform_parameter_var.get() != "2" or not app._last_transform or not app.before_canvas.find_all() or not app.after_canvas.find_all():
        root.destroy()
        raise RuntimeError("native transform visualizer did not select a pivot and render both sequences")
    app._show_view("conjecture")
    _log("window_mapped", toolkit="tkinter")
    root.after(800, root.destroy)
    root.mainloop()
    _log("window_smoke_passed", toolkit="tkinter")


def main(argv=None) -> None:
    import argparse

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--startup-check", action="store_true")
    parser.add_argument("--window-smoke-check", action="store_true")
    args, _unknown = parser.parse_known_args(argv)
    log_path = _open_startup_log()
    _log("main_entered", mode="window_smoke_check" if args.window_smoke_check else "startup_check" if args.startup_check else "desktop")
    try:
        if args.startup_check:
            _startup_check()
            return
        if args.window_smoke_check:
            _window_smoke_check()
            return
        root = tk.Tk()
        DesktopWorkbench(root)
        _log("window_created", title=root.title())
        root.mainloop()
        _log("window_closed")
    except Exception:
        details = traceback.format_exc()
        _log("fatal_exception", traceback=details)
        if __import__("sys").platform == "darwin" and not args.startup_check and not args.window_smoke_check:
            try:
                import subprocess
                script = 'display dialog ' + json.dumps(f"Ascent Engine could not start. Diagnostic log: {log_path}") + ' with title "Ascent Engine" buttons {"OK"}'
                subprocess.run(["osascript", "-e", script], check=False, timeout=15)
            except Exception:
                pass
        raise


if __name__ == "__main__":
    main()
