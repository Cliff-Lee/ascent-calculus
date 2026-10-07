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


class DropLane(tk.Frame):
    """Native drop target accepting pattern blocks from the palette."""

    def __init__(self, master, app: "DesktopWorkbench", side: str):
        super().__init__(master, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        self.app, self.side = app, side
        self.bind("<Enter>", lambda _e: self._highlight(True))
        self.bind("<Leave>", lambda _e: self._highlight(False))
        self.columnconfigure(0, weight=1)
        self.family = ttk.Combobox(self, state="readonly", values=FAMILIES, width=15)
        self.family.set("modified")
        self.family.grid(row=0, column=0, sticky="w", padx=14, pady=(14, 8))
        self.family.bind("<<ComboboxSelected>>", lambda _e: self.app.changed())
        self.count = tk.Label(self, text="0 pattern rules", bg=PANEL, fg=MUTED, font=("TkDefaultFont", 9))
        self.count.grid(row=0, column=1, sticky="e", padx=14)
        self.chips = tk.Frame(self, bg=PANEL)
        self.chips.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10)
        self.empty = tk.Label(self, text="Drop a pattern here  ·  e.g.  2122", bg="#f8faf8", fg="#87938d", font=("TkDefaultFont", 10), pady=14, highlightthickness=1, highlightbackground=LINE)
        self.empty.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(4, 14))

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
        self.root.geometry("1420x900")
        self.root.minsize(1120, 740)
        self.root.configure(bg=BG)
        self.drag_payload = None
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
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=INK, rowheight=34, bordercolor=LINE, font=("TkDefaultFont", 10))
        style.configure("Treeview.Heading", background="#f0f4f1", foreground=MUTED, relief="flat", font=("TkDefaultFont", 9, "bold"), padding=(8, 9))
        style.map("Treeview", background=[("selected", MINT)], foreground=[("selected", INK)])
        style.configure("Horizontal.TProgressbar", troughcolor="#e8eeea", background=GREEN, bordercolor="#e8eeea", lightcolor=GREEN, darkcolor=GREEN)

    def _build(self):
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)
        header = tk.Frame(self.root, bg=INK, height=76)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        tk.Label(header, text="A", bg=GREEN, fg="white", font=("TkDefaultFont", 15, "bold"), width=3, height=1).pack(side="left", padx=(24, 12), pady=18)
        titlebox = tk.Frame(header, bg=INK)
        titlebox.pack(side="left", pady=13)
        tk.Label(titlebox, text="Ascent Engine", bg=INK, fg="white", font=("TkDefaultFont", 17, "bold")).pack(anchor="w")
        tk.Label(titlebox, text="A workbench for sequence conjectures", bg=INK, fg="#b9cbc2", font=("TkDefaultFont", 9)).pack(anchor="w", pady=(2, 0))
        self.header_status = tk.Label(header, text="LOCAL · FINITE TESTS", bg=INK, fg="#b9cbc2", font=("TkDefaultFont", 9, "bold"))
        self.header_status.pack(side="right", padx=26)

        body = tk.Frame(self.root, bg=BG)
        body.grid(row=1, column=0, sticky="nsew", padx=22, pady=18)
        body.columnconfigure(0, weight=0, minsize=238)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        self._build_palette(body)
        self._build_workspace(body)

    def _build_palette(self, parent):
        rail = tk.Frame(parent, bg=BG, width=238)
        rail.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        rail.grid_propagate(False)
        tk.Label(rail, text="BUILDING BLOCKS", bg=BG, fg=MUTED, font=("TkDefaultFont", 9, "bold")).pack(anchor="w", pady=(4, 10))
        card = tk.Frame(rail, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        card.pack(fill="x")
        tk.Label(card, text="PATTERN RULES", bg=PANEL, fg=INK, font=("TkDefaultFont", 9, "bold")).pack(anchor="w", padx=14, pady=(14, 4))
        tk.Label(card, text="Drag a rule into either class.", bg=PANEL, fg=MUTED, font=("TkDefaultFont", 9), wraplength=195, justify="left").pack(anchor="w", padx=14, pady=(0, 9))
        for mode, caption, mode_bg, mode_fg in (("avoid", "Avoid", "#fff0e9", "#965233"), ("contain", "Contain", MINT, GREEN_DARK)):
            tk.Label(card, text=caption.upper(), bg=PANEL, fg=MUTED, font=("TkDefaultFont", 8, "bold")).pack(anchor="w", padx=14, pady=(8, 4))
            for pattern in PATTERNS:
                block = tk.Label(card, text=f"⟨{pattern}⟩", bg=mode_bg, fg=mode_fg, font=("TkDefaultFont", 10, "bold"), padx=10, pady=7, cursor="hand2", anchor="w")
                block.pack(fill="x", padx=12, pady=3)
                block.bind("<ButtonPress-1>", lambda e, m=mode, p=pattern: self._drag_start(e, m, p))
                block.bind("<B1-Motion>", self._drag_motion)
                block.bind("<ButtonRelease-1>", self._drag_end)
        saved = tk.Frame(rail, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        saved.pack(fill="both", expand=True, pady=(14, 0))
        top = tk.Frame(saved, bg=PANEL)
        top.pack(fill="x", padx=12, pady=(12, 8))
        tk.Label(top, text="SAVED TESTS", bg=PANEL, fg=INK, font=("TkDefaultFont", 9, "bold")).pack(side="left")
        tk.Button(top, text="Save current", command=self.save_current, relief="flat", bg=PANEL, fg=GREEN, activebackground=PANEL, cursor="hand2", font=("TkDefaultFont", 8, "bold")).pack(side="right")
        self.saved_list = tk.Listbox(saved, height=7, relief="flat", borderwidth=0, highlightthickness=0, activestyle="none", bg=PANEL, fg=INK, selectbackground=MINT, selectforeground=INK, font=("TkDefaultFont", 9))
        self.saved_list.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        self.saved_list.bind("<Double-Button-1>", self.load_saved)
        self._render_saved()
        actions = tk.Frame(saved, bg=PANEL)
        actions.pack(fill="x", padx=10, pady=(0, 9))
        tk.Button(actions, text="Export", command=self.export_state, relief="flat", bg="#f0f4f1", fg=INK, activebackground=MINT, cursor="hand2", font=("TkDefaultFont", 9), padx=9, pady=5).pack(side="left")
        tk.Button(actions, text="Import", command=self.import_state, relief="flat", bg="#f0f4f1", fg=INK, activebackground=MINT, cursor="hand2", font=("TkDefaultFont", 9), padx=9, pady=5).pack(side="left", padx=6)

    def _build_workspace(self, parent):
        work = tk.Frame(parent, bg=BG)
        work.grid(row=0, column=1, sticky="nsew")
        work.columnconfigure(0, weight=1)
        work.rowconfigure(2, weight=1)
        intro = tk.Frame(work, bg=BG)
        intro.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        tk.Label(intro, text="Test a conjecture", bg=BG, fg=INK, font=("TkDefaultFont", 22, "bold")).pack(anchor="w")
        tk.Label(intro, text="Compose two classes, set a finite range, and inspect the first counterexample.", bg=BG, fg=MUTED, font=("TkDefaultFont", 10)).pack(anchor="w", pady=(4, 0))

        composer = tk.Frame(work, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        composer.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        composer.columnconfigure(0, weight=1)
        tk.Label(composer, text="CONJECTURE COMPOSER", bg=PANEL, fg=MUTED, font=("TkDefaultFont", 9, "bold")).grid(row=0, column=0, sticky="w", padx=16, pady=(13, 8))
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
        tk.Label(question, text="to", bg=PANEL, fg=MUTED).pack(side="left")
        self.stop_box = ttk.Spinbox(question, from_=1, to=11, width=4, textvariable=self.stop_var, command=self.changed)
        self.stop_box.pack(side="left", padx=(5, 14))
        tk.Label(question, text="Refine counts by", bg=PANEL, fg=MUTED, font=("TkDefaultFont", 9)).pack(side="left", padx=(5, 7))
        self.stat_var = tk.StringVar(value="none")
        self.stat_box = ttk.Combobox(question, state="readonly", width=23, textvariable=self.stat_var, values=[key for key in STATISTICS])
        self.stat_box.pack(side="left")
        self.stat_box.bind("<<ComboboxSelected>>", lambda _e: self.changed())
        self.start_var.trace_add("write", lambda *_: self.changed())
        self.stop_var.trace_add("write", lambda *_: self.changed())
        self.question_text = tk.Label(composer, text="", bg=MINT, fg=GREEN_DARK, font=("TkDefaultFont", 10), justify="left", anchor="w", padx=14, pady=10, wraplength=1000)
        self.question_text.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))

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
        columns = ("n", "left", "right", "difference", "status")
        self.table = ttk.Treeview(results, columns=columns, show="headings", selectmode="browse")
        for key, title, width, anchor in (("n", "DEGREE n", 95, "center"), ("left", "CLASS A", 160, "e"), ("right", "CLASS B", 160, "e"), ("difference", "A − B", 145, "e"), ("status", "RESULT", 180, "w")):
            self.table.heading(key, text=title)
            self.table.column(key, width=width, anchor=anchor, stretch=key == "status")
        self.table.grid(row=2, column=0, sticky="nsew", padx=15, pady=(0, 8))
        self.table.tag_configure("match", foreground=GREEN_DARK)
        self.table.tag_configure("diverge", foreground=RED, background="#fff6f4")
        self.footer = tk.Label(results, text="Choose patterns from the left, then drop them into either class.", bg="#f8faf8", fg=MUTED, anchor="w", padx=14, pady=9, font=("TkDefaultFont", 9))
        self.footer.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))

    def _drag_start(self, event, mode, pattern):
        self.drag_payload = {"mode": mode, "pattern": pattern}
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

    def remove_rule(self, side, index):
        del self.rules[side][index]
        self.left_lane.render(); self.right_lane.render(); self.changed()

    def _display_family(self, family):
        return FAMILY_LABELS.get(family, family.title())

    def _refresh_conjecture(self):
        try:
            start, stop = int(self.start_var.get()), int(self.stop_var.get())
        except ValueError:
            start, stop = 1, 8
        def describe(side):
            lane = self.left_lane if side == "left" else self.right_lane
            family = self._display_family(lane.family.get())
            rules = self.rules[side]
            if not rules:
                return f"all {family} ascent sequences"
            parts = [f"{r['mode']} ⟨{', '.join(map(str, r['pattern']))}⟩" for r in rules]
            return f"{family} ascent sequences that " + " and ".join(parts)
        stat = self.stat_var.get()
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
        left_family, right_family = self.left_lane.family.get(), self.right_lane.family.get()
        for label, family in (("Class A", left_family), ("Class B", right_family)):
            if stop > FAMILY_LIMITS[family]:
                raise ValueError(f"{label} generation is bounded to degree {FAMILY_LIMITS[family]} for {family} sequences.")
        return {"question": "compare", "start": start, "stop": stop, "statistic": self.stat_var.get(), "left": _side(left_family, self.rules["left"]), "right": _side(right_family, self.rules["right"])}

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
        return {"left_family": self.left_lane.family.get(), "right_family": self.right_lane.family.get(), "left_rules": json.dumps(self.rules["left"]), "right_rules": json.dumps(self.rules["right"]), "start": self.start_var.get(), "stop": self.stop_var.get(), "statistic": self.stat_var.get()}

    def _restore_draft(self):
        draft = self.state.get("draft", {})
        if not isinstance(draft, dict):
            return
        for side, lane in (("left", self.left_lane), ("right", self.right_lane)):
            family = draft.get(f"{side}_family")
            if family in FAMILIES:
                lane.family.set(family)
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
        self.stat_var.set(stat if stat in STATISTICS else "none")

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
        for item in self.state.get("saved", []):
            self.saved_list.insert("end", item.get("name", "Saved conjecture"))

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
        self.left_lane.family.set(spec.get("left", {}).get("family", "modified"))
        self.right_lane.family.set(spec.get("right", {}).get("family", "modified"))
        self.rules["left"] = spec.get("left", {}).get("rules", [])
        self.rules["right"] = spec.get("right", {}).get("rules", [])
        self.start_var.set(str(spec.get("start", 1))); self.stop_var.set(str(spec.get("stop", 8)))
        self.stat_var.set(spec.get("statistic", "none"))
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
    DesktopWorkbench(root)
    root.update()
    if not root.winfo_ismapped():
        root.destroy()
        raise RuntimeError("native Tk window was not mapped")
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
