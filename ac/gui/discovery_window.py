"""Native interface for persistent transformation-family discovery jobs."""

from __future__ import annotations

import json
import sqlite3
import tkinter as tk
from types import SimpleNamespace
from tkinter import filedialog, messagebox, ttk

from ac.discovery.dossiers import build_research_dossier, write_dossier
from ac.discovery.jobs import ResearchJobStore, default_job_database
from ac.discovery.significance import build_research_priority_review
from ac.discovery.experiment_design import build_experiment_design_options
from ac.discovery.experiment_refinement import (
    build_experiment_refinement_options,
    build_refinement_context,
    validate_experiment_refinement,
)
from ac.discovery.transformation_family import TransformationFamilySearchSpec
from ac.discovery.proof_assistance import build_proof_assistance_context
from ac.discovery.overnight_campaign import (
    MAX_REFINEMENTS,
    MAX_TOTAL_CANDIDATES,
    MAX_WALL_SECONDS,
    OVERNIGHT_HANDLER_ID,
)
from ac.gui.discovery_campaign import build_transformation_family_spec
from ac.ai import AIAssistantSettings, ProviderLocality, default_ai_settings_path, load_ai_settings
from ac.gui.ai_assistant import AIAssistantSettingsDialog, AIExperimentDesignerDialog, AIExplanationDialog, AIProofPlanDialog, build_candidate_evidence


BG = "#f3f5f2"
PANEL = "#ffffff"
INK = "#18231f"
MUTED = "#66746e"
LINE = "#dce3de"
GREEN = "#176c52"
GREEN_DARK = "#10553f"
AMBER = "#a35b1b"
RED = "#a8443c"
FAMILIES = ("ordinary", "modified", "revised")
HANDLER = "search-transformation-families"
CAMPAIGN_HANDLERS = {HANDLER, OVERNIGHT_HANDLER_ID}


def _overnight_state(job):
    checkpoint = job.checkpoint if isinstance(job.checkpoint, dict) else {}
    return checkpoint if checkpoint.get("overnight_checkpoint_version") else {}


def _latest_campaign_result(job):
    if job.handler == OVERNIGHT_HANDLER_ID:
        report = (job.result or {}).get("overnight_campaign", {})
        latest = (job.result or {}).get("latest_search_result")
        if latest is None and report.get("completed_rounds"):
            latest = report["completed_rounds"][-1].get("search_result")
        if latest:
            return latest
        state = _overnight_state(job)
        active = state.get("active_search_checkpoint", {})
        rounds = state.get("completed_rounds", ())
        if active and active.get("examined", 0) and state.get("round_index", 0) >= len(rounds):
            return {
                "exact_candidates": active.get("exact_candidates", []),
                "ranked_candidates": active.get("ranked_candidates", []),
                "candidates_tested": active.get("examined", 0),
            }
        if active and not rounds:
            return {
                "exact_candidates": active.get("exact_candidates", []),
                "ranked_candidates": active.get("ranked_candidates", []),
                "candidates_tested": active.get("examined", 0),
            }
        return rounds[-1].get("search_result") if rounds else None
    if job.result:
        return job.result
    return job.checkpoint


def _latest_campaign_spec(job):
    if job.handler != OVERNIGHT_HANDLER_ID:
        return job.question
    state = _overnight_state(job)
    active = state.get("active_search_checkpoint", {})
    if active and (active.get("ranked_candidates") or active.get("exact_candidates")):
        raw = state.get("active_specification")
    elif state.get("completed_rounds"):
        raw = state["completed_rounds"][-1].get("specification")
    else:
        report = (job.result or {}).get("overnight_campaign", {})
        if report.get("completed_rounds"):
            raw = report["completed_rounds"][-1].get("specification")
        else:
            raw = (job.result or {}).get("latest_specification") or state.get("active_specification")
    if raw:
        try:
            return TransformationFamilySearchSpec.from_dict(raw)
        except (TypeError, ValueError, KeyError):
            pass
    return job.question


def _candidate_rows(job):
    result = _latest_campaign_result(job) or {}
    groups = (result.get("exact_candidates", ()), result.get("ranked_candidates", ()))
    rows, seen = [], set()
    for group in groups:
        for row in group:
            key = row.get("program")
            if key not in seen:
                seen.add(key)
                rows.append(row)
    rows.sort(key=lambda row: (
        not row.get("bijection_on_every_scenario", False),
        -row.get("matching_scenario_count", 0),
        row.get("cost", 0),
        row.get("program", ""),
    ))
    return rows


def _scenario_map_previews(row):
    """Return scenario-indexed map previews, including legacy first-map rows."""
    if not isinstance(row, dict):
        return ()
    previews = row.get("scenario_map_previews")
    if isinstance(previews, (list, tuple)):
        return tuple(
            item for item in previews
            if isinstance(item, dict) and isinstance(item.get("example_map"), dict)
        )
    legacy = row.get("example_map_preview")
    if isinstance(legacy, dict):
        return ({
            "scenario_index": 0,
            "scenario_fingerprint": legacy.get("scenario_fingerprint"),
            "example_map": legacy,
        },)
    return ()


def _failure_text(failure):
    if not failure:
        return ""
    bits = [f"first failure: {failure.get('kind', 'unknown')} at base n={failure.get('base_degree', '?')}" ]
    for field, label in (("source", "source"), ("other_source", "other source"), ("output", "output")):
        value = failure.get(field)
        if value:
            bits.append(f"{label}={value.get('values')} (height {value.get('height')})")
    if failure.get("detail"):
        bits.append(failure["detail"])
    return "; ".join(bits)


def _candidate_has_failure(row):
    if not isinstance(row, dict):
        return False
    for item in row.get("scenario_results", ()):
        evaluation = item.get("evaluation", {}) if isinstance(item, dict) else {}
        if isinstance(evaluation, dict) and isinstance(evaluation.get("first_failure") or evaluation.get("counterexample"), dict):
            return True
    return False


def _scenario_evidence_lines(row):
    """Format the candidate's finite result and map sample for every scenario."""
    previews_by_scenario = {
        item.get("scenario_index"): item.get("example_map")
        for item in _scenario_map_previews(row)
    }
    lines = []
    for item in row.get("scenario_results", ()):
        status = "MATCH" if item.get("finite_match") else "does not match"
        scenario_index = item.get("scenario_index")
        display_index = scenario_index + 1 if isinstance(scenario_index, int) else "?"
        lines.append(f"\nScenario {display_index}: {item.get('source_class')} → {item.get('target_class')} · degrees n{item.get('source_offset', 0):+d} → n{item.get('target_offset', 0):+d} · {status} through base n={item.get('verified_through', '?')}")
        evaluation = item.get("evaluation", {})
        failure = evaluation.get("first_failure")
        if failure:
            lines.append(_failure_text(failure))
        preview = previews_by_scenario.get(scenario_index)
        if preview:
            lines.append(f"Sample map at base n={preview['base_degree']}: {preview['source']['values']} → {preview['output']['values']}")
            lines.append(f"Position map: {preview['position_map']} · value map: {preview['value_map']} · created positions: {preview['created_positions']}")
            if preview.get("block_trace"):
                lines.append(f"Block trace: {preview['block_trace']}")
    return lines


class DiscoveryCampaignWindow:
    """A resumable class/offset campaign browser attached to the desktop app."""

    def __init__(self, parent, *, ensure_worker, on_preview, database=None):
        self.parent = parent
        self.ensure_worker = ensure_worker
        self.on_preview = on_preview
        self.store = ResearchJobStore(database or default_job_database())
        self.window = tk.Toplevel(parent)
        self.window.title("Discover transformations across classes and offsets")
        self.window.geometry("1120x790")
        self.window.minsize(920, 650)
        self.window.configure(bg=BG)
        self.window.protocol("WM_DELETE_WINDOW", self.window.withdraw)
        self._rows_by_iid = {}
        self._candidate_by_iid = {}
        self._active_job_id = None
        self.ai_settings_path = default_ai_settings_path()
        self.ai_settings_error = None
        try:
            self.ai_settings = load_ai_settings(self.ai_settings_path)
        except ValueError as exc:
            self.ai_settings = AIAssistantSettings()
            self.ai_settings_error = str(exc)
        self.ai_model_locality = ProviderLocality.UNKNOWN
        self.ai_dialog = None
        self.ai_design_dialog = None
        self.ai_proof_dialog = None
        self._pending_experiment_design = None
        self._build()
        self.refresh()
        self._schedule_refresh()

    def show(self):
        self.window.deiconify()
        self.window.lift()
        self.refresh()

    def _build(self):
        root = self.window
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)
        intro = tk.Frame(root, bg=BG)
        intro.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 8))
        intro_top = tk.Frame(intro, bg=BG)
        intro_top.pack(fill="x")
        tk.Label(intro_top, text="Search transformation families", bg=BG, fg=INK, font=("TkDefaultFont", 18, "bold")).pack(side="left", anchor="w")
        self.ai_settings_button = tk.Button(
            intro_top, text=self._ai_settings_label(), command=self.configure_ai,
            relief="flat", bg="#e8eeea", fg=GREEN_DARK, activebackground="#dce9e1",
            cursor="hand2", font=("TkDefaultFont", 8, "bold"), padx=10, pady=6,
        )
        self.ai_settings_button.pack(side="right")
        self.design_button = tk.Button(
            intro_top, text="Design experiment…", command=self.design_experiment,
            relief="flat", bg=GREEN, fg="white", activebackground=GREEN_DARK,
            cursor="hand2", font=("TkDefaultFont", 8, "bold"), padx=10, pady=6,
        )
        self.design_button.pack(side="right", padx=(0, 7))
        tk.Label(intro, text="Generate bounded map programs, then test each across the selected pattern classes and degree offsets. Matching every row is finite evidence, not a proof.", bg=BG, fg=MUTED, font=("TkDefaultFont", 9), wraplength=1000, justify="left").pack(anchor="w", pady=(3, 0))

        form = tk.Frame(root, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        form.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))
        for column in range(12):
            form.columnconfigure(column, weight=1 if column in {1, 3, 5, 7, 9} else 0)
        self.source_family = tk.StringVar(value="modified")
        self.target_family = tk.StringVar(value="revised")
        self.rule_mode = tk.StringVar(value="avoid")
        self.source_patterns = tk.StringVar(value="111, 2122")
        self.target_patterns = tk.StringVar(value="111, 2122")
        self.offsets = tk.StringVar(value="0:+2, 0:0")
        self.start = tk.StringVar(value="1")
        self.stop = tk.StringVar(value="4")
        self.max_cost = tk.StringVar(value="4")
        self.max_steps = tk.StringVar(value="2")
        self.candidate_budget = tk.StringVar(value="250")
        self._field(form, "SOURCE", self.source_family, 0, 0, values=FAMILIES)
        self._field(form, "TARGET", self.target_family, 0, 2, values=FAMILIES)
        self._field(form, "PATTERN RULE", self.rule_mode, 0, 4, values=("avoid", "contain"))
        self._field(form, "BASE n FROM", self.start, 0, 6, width=6)
        self._field(form, "TO", self.stop, 0, 8, width=6)
        self._field(form, "MAX COST", self.max_cost, 0, 10, width=6)
        self._field(form, "SOURCE PATTERNS", self.source_patterns, 2, 0, width=24, span=4)
        self._field(form, "TARGET PATTERNS", self.target_patterns, 2, 4, width=24, span=4)
        self._field(form, "SOURCE:TARGET OFFSETS", self.offsets, 2, 8, width=19, span=3)
        self._field(form, "MAX STEPS", self.max_steps, 4, 0, width=6)
        self._field(form, "CANDIDATE BUDGET", self.candidate_budget, 4, 2, width=9)
        self.start_button = tk.Button(form, text="Start campaign", command=self.start_campaign, relief="flat", bg=GREEN, fg="white", activebackground=GREEN_DARK, cursor="hand2", font=("TkDefaultFont", 9, "bold"), padx=13, pady=7)
        self.start_button.grid(row=4, column=10, columnspan=2, sticky="e", padx=12, pady=(4, 10))
        self.overnight_button = tk.Button(
            form, text="Run overnight with AI…", command=self.start_overnight_campaign,
            relief="flat", bg="#f3ead8", fg="#754415", activebackground="#eadcc3",
            cursor="hand2", font=("TkDefaultFont", 8, "bold"), padx=10, pady=7,
        )
        self.overnight_button.grid(row=4, column=7, columnspan=3, sticky="e", padx=(4, 8), pady=(4, 10))
        self.form_note = tk.Label(form, text="Comma-separated patterns; use * for the unrestricted class. Offsets compare source n+a with target n+b. Increase cost, steps, or candidates for broader searches.", bg=PANEL, fg=MUTED, font=("TkDefaultFont", 8), wraplength=1050, justify="left")
        self.form_note.grid(row=6, column=0, columnspan=12, sticky="w", padx=12, pady=(0, 10))

        body = ttk.Panedwindow(root, orient="horizontal")
        body.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 16))
        jobs_frame = tk.Frame(body, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        results_frame = tk.Frame(body, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        body.add(jobs_frame, weight=1)
        body.add(results_frame, weight=3)
        jobs_frame.columnconfigure(0, weight=1)
        jobs_frame.rowconfigure(1, weight=1)
        tk.Label(jobs_frame, text="SAVED CAMPAIGNS", bg=PANEL, fg=MUTED, font=("TkDefaultFont", 8, "bold")).grid(row=0, column=0, sticky="w", padx=11, pady=(11, 6))
        self.jobs_table = ttk.Treeview(jobs_frame, columns=("status", "progress"), show="tree headings", selectmode="browse")
        self.jobs_table.heading("#0", text="Campaign")
        self.jobs_table.heading("status", text="Status")
        self.jobs_table.heading("progress", text="Progress")
        self.jobs_table.column("#0", width=175, stretch=True)
        self.jobs_table.column("status", width=78, stretch=False)
        self.jobs_table.column("progress", width=85, stretch=False)
        self.jobs_table.grid(row=1, column=0, sticky="nsew", padx=9)
        self.jobs_table.bind("<<TreeviewSelect>>", self._job_selected)
        jobs_scroll = ttk.Scrollbar(jobs_frame, orient="vertical", command=self.jobs_table.yview)
        jobs_scroll.grid(row=1, column=1, sticky="ns", pady=2)
        self.jobs_table.configure(yscrollcommand=jobs_scroll.set)
        job_actions = tk.Frame(jobs_frame, bg=PANEL)
        job_actions.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        for label, action in (("Pause", self.pause_selected), ("Resume", self.resume_selected), ("Cancel", self.cancel_selected), ("Checkpoint", self.show_checkpoint), ("Refresh", self.refresh)):
            tk.Button(job_actions, text=label, command=action, relief="flat", bg="#edf3ef", fg=GREEN_DARK, activebackground="#e1eee7", cursor="hand2", font=("TkDefaultFont", 8, "bold"), padx=7, pady=5).pack(side="left", padx=2)

        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(3, weight=2)
        results_frame.rowconfigure(5, weight=3)
        self.job_summary = tk.Label(results_frame, text="Select a saved campaign or start a new one.", bg=PANEL, fg=INK, font=("TkDefaultFont", 9, "bold"), anchor="w", justify="left", wraplength=730)
        self.job_summary.grid(row=0, column=0, sticky="ew", padx=12, pady=(11, 3))
        self.progress_text = tk.Label(results_frame, text="", bg=PANEL, fg=MUTED, font=("TkDefaultFont", 8), anchor="w")
        self.progress_text.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 3))
        self.progress = ttk.Progressbar(results_frame, mode="determinate", maximum=1)
        self.progress.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))
        self.candidate_table = ttk.Treeview(results_frame, columns=("support", "priority", "cost", "program"), show="headings", selectmode="browse", height=8)
        for key, label in (("support", "Scenarios"), ("priority", "Priority"), ("cost", "Cost"), ("program", "Generated program")):
            self.candidate_table.heading(key, text=label)
        self.candidate_table.column("support", width=78, stretch=False, anchor="center")
        self.candidate_table.column("priority", width=76, stretch=False, anchor="center")
        self.candidate_table.column("cost", width=52, stretch=False, anchor="center")
        self.candidate_table.column("program", width=410, stretch=True)
        self.candidate_table.grid(row=3, column=0, sticky="nsew", padx=10)
        self.candidate_table.bind("<<TreeviewSelect>>", self._candidate_selected)
        self.candidate_table.tag_configure("exact", foreground=GREEN_DARK)
        candidates_scroll = ttk.Scrollbar(results_frame, orient="vertical", command=self.candidate_table.yview)
        candidates_scroll.grid(row=3, column=1, sticky="ns")
        self.candidate_table.configure(yscrollcommand=candidates_scroll.set)
        tk.Label(results_frame, text="CANDIDATE EVIDENCE · Priority is a transparent triage score, not theorem likelihood", bg=PANEL, fg=MUTED, font=("TkDefaultFont", 8, "bold")).grid(row=4, column=0, sticky="w", padx=12, pady=(9, 4))
        detail_frame = tk.Frame(results_frame, bg="#f8faf8")
        detail_frame.grid(row=5, column=0, sticky="nsew", padx=10)
        detail_frame.columnconfigure(0, weight=1)
        detail_frame.rowconfigure(0, weight=1)
        self.detail = tk.Text(detail_frame, wrap="word", height=8, bg="#f8faf8", fg=INK, relief="flat", font=("TkDefaultFont", 9), padx=8, pady=7)
        self.detail.grid(row=0, column=0, sticky="nsew")
        detail_scroll = ttk.Scrollbar(detail_frame, orient="vertical", command=self.detail.yview)
        detail_scroll.grid(row=0, column=1, sticky="ns")
        self.detail.configure(yscrollcommand=detail_scroll.set, state="disabled")
        bottom = tk.Frame(results_frame, bg=PANEL)
        bottom.grid(row=6, column=0, sticky="ew", padx=10, pady=8)
        self.memory_label = tk.Label(bottom, text="", bg=PANEL, fg=MUTED, font=("TkDefaultFont", 8), anchor="w")
        self.memory_label.pack(side="left", fill="x", expand=True)
        self.preview_button = tk.Button(bottom, text="Preview sample map", command=self.preview_selected, state="disabled", relief="flat", bg="#e8f2ec", fg=GREEN_DARK, activebackground="#e1eee7", cursor="hand2", font=("TkDefaultFont", 8, "bold"), padx=9, pady=5)
        self.preview_button.pack(side="right")
        self.refine_button = tk.Button(bottom, text="Refine from failure…", command=self.refine_selected, state="disabled", relief="flat", bg="#f6efe3", fg="#7e4a16", activebackground="#efe1ca", cursor="hand2", font=("TkDefaultFont", 8, "bold"), padx=9, pady=5)
        self.refine_button.pack(side="right", padx=(0, 6))
        self.ask_ai_button = tk.Button(bottom, text="Ask Ollama", command=self.ask_about_candidate, state="disabled", relief="flat", bg=GREEN, fg="white", activebackground=GREEN_DARK, cursor="hand2", font=("TkDefaultFont", 8, "bold"), padx=9, pady=5)
        self.ask_ai_button.pack(side="right", padx=(0, 6))
        self.proof_plan_button = tk.Button(bottom, text="Build proof plan…", command=self.plan_proof_selected, state="disabled", relief="flat", bg="#e9f0eb", fg=GREEN_DARK, activebackground="#dce9e1", cursor="hand2", font=("TkDefaultFont", 8, "bold"), padx=9, pady=5)
        self.proof_plan_button.pack(side="right", padx=(0, 6))
        self.export_button = tk.Button(bottom, text="Export dossier…", command=self.export_selected, relief="flat", bg="#edf3ef", fg=GREEN_DARK, activebackground="#e1eee7", cursor="hand2", font=("TkDefaultFont", 8, "bold"), padx=9, pady=5)
        self.export_button.pack(side="right", padx=(0, 6))

    @staticmethod
    def _field(parent, label, variable, row, column, *, values=None, width=12, span=1):
        tk.Label(parent, text=label, bg=PANEL, fg=MUTED, font=("TkDefaultFont", 7, "bold")).grid(row=row, column=column, sticky="w", padx=(12, 4), pady=(9, 3))
        if values:
            widget = ttk.Combobox(parent, state="readonly", width=width, textvariable=variable, values=values)
        else:
            widget = ttk.Entry(parent, width=width, textvariable=variable)
        widget.grid(row=row + 1, column=column, columnspan=span, sticky="ew", padx=(12, 8), pady=(0, 8))
        return widget

    def start_campaign(self):
        try:
            spec = self._form_spec()
            options = {}
            if self._pending_experiment_design is not None:
                design, provenance = self._pending_experiment_design
                refinement_data = provenance.get("refinement")
                if refinement_data is not None:
                    context = refinement_data["context"]
                    refinement = validate_experiment_refinement(
                        json.loads(provenance["response_text"]), context,
                    )
                    options = build_experiment_refinement_options(
                        design=design,
                        provenance=provenance,
                        context=context,
                        refinement=refinement,
                        applied_spec_fingerprint=spec.fingerprint,
                    )
                else:
                    options = build_experiment_design_options(
                        question=provenance["question"],
                        endpoint=provenance["endpoint"],
                        model=provenance["requested_model"],
                        response_model=provenance["response_model"],
                        provider_id=provenance["provider_id"],
                        inference_locality=provenance["inference_locality"],
                        requested_at=provenance["requested_at"],
                        completed_at=provenance["completed_at"],
                        system_prompt=provenance["system_prompt"],
                        user_prompt=provenance["user_prompt"],
                        response_text=provenance["response_text"],
                        parameters=provenance["parameters"],
                        design=design,
                        applied_spec_fingerprint=spec.fingerprint,
                    )
            job = self.store.create_job(spec, handler=HANDLER, options=options)
            self._pending_experiment_design = None
            self.form_note.configure(
                text="Campaign saved. All candidate evaluation is performed by the deterministic engine; finite matches are not proofs.",
                fg=GREEN_DARK,
            )
            self._active_job_id = job.id
            self.ensure_worker()
            self.refresh(select_id=job.id)
        except (ValueError, TypeError, OSError, RuntimeError) as exc:
            messagebox.showerror("Campaign settings", str(exc), parent=self.window)

    def _form_spec(self):
        return build_transformation_family_spec(
            source_family=self.source_family.get(),
            target_family=self.target_family.get(),
            rule_mode=self.rule_mode.get(),
            source_patterns=self.source_patterns.get(),
            target_patterns=self.target_patterns.get(),
            offsets=self.offsets.get(),
            start=int(self.start.get()),
            stop=int(self.stop.get()),
            max_cost=int(self.max_cost.get()),
            max_steps=int(self.max_steps.get()),
            candidate_budget=int(self.candidate_budget.get()),
        )

    def start_overnight_campaign(self):
        if not self.ai_settings.enabled or not self.ai_settings.model.strip():
            messagebox.showinfo(
                "Configure Ollama first",
                "Enable Ollama and select a model in the top-right AI settings before starting an autonomous campaign.",
                parent=self.window,
            )
            self.configure_ai()
            return
        try:
            spec = self._form_spec()
        except (ValueError, TypeError) as exc:
            messagebox.showerror("Campaign settings", str(exc), parent=self.window)
            return

        dialog = tk.Toplevel(self.window)
        dialog.title("Run an overnight research campaign")
        dialog.transient(self.window)
        dialog.grab_set()
        dialog.configure(bg=BG)
        dialog.resizable(False, False)
        refinements = tk.StringVar(value="3")
        candidates = tk.StringVar(value=str(min(MAX_TOTAL_CANDIDATES, max(1000, spec.candidate_budget))))
        hours = tk.StringVar(value="8")
        panel = tk.Frame(dialog, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        panel.pack(fill="both", expand=True, padx=16, pady=16)
        tk.Label(panel, text="Budget the search", bg=PANEL, fg=INK, font=("TkDefaultFont", 13, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(14, 5))
        tk.Label(
            panel,
            text=(
                f"The worker runs the deterministic search, asks {self.ai_settings.model} for a bounded follow-up "
                f"from exact failures, validates it, then searches again. Model locality: {self.ai_model_locality.value}. "
                "The configured loopback Ollama endpoint receives the prompt; cloud models may offload inference. "
                "The elapsed-time limit includes pauses. Every round and prompt is saved for export. Matches remain finite evidence."
            ),
            bg=PANEL, fg=MUTED, font=("TkDefaultFont", 8), wraplength=470, justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=14, pady=(0, 10))
        for row, (label, variable, suffix) in enumerate((
            ("AI refinement rounds", refinements, f"1–{MAX_REFINEMENTS}"),
            ("Total candidate programs", candidates, f"1–{MAX_TOTAL_CANDIDATES:,}"),
            ("Elapsed hours", hours, f"1–{MAX_WALL_SECONDS // 3600}"),
        ), start=2):
            tk.Label(panel, text=label, bg=PANEL, fg=INK, font=("TkDefaultFont", 9, "bold")).grid(row=row, column=0, sticky="w", padx=14, pady=5)
            field = ttk.Entry(panel, width=12, textvariable=variable)
            field.grid(row=row, column=1, sticky="e", padx=(8, 14), pady=5)
            tk.Label(panel, text=suffix, bg=PANEL, fg=MUTED, font=("TkDefaultFont", 8)).grid(row=row, column=2, sticky="w", padx=(0, 14), pady=5)
        actions = tk.Frame(panel, bg=PANEL)
        actions.grid(row=5, column=0, columnspan=3, sticky="e", padx=14, pady=(12, 14))
        tk.Button(actions, text="Cancel", command=dialog.destroy, relief="flat", bg="#edf3ef", fg=GREEN_DARK, padx=12, pady=6).pack(side="right")

        def launch():
            try:
                round_budget = int(refinements.get())
                candidate_budget = int(candidates.get())
                hours_budget = int(hours.get())
                if not 1 <= round_budget <= MAX_REFINEMENTS:
                    raise ValueError(f"AI refinement rounds must be from 1 through {MAX_REFINEMENTS}.")
                if not 1 <= candidate_budget <= MAX_TOTAL_CANDIDATES:
                    raise ValueError(f"Total candidate programs must be from 1 through {MAX_TOTAL_CANDIDATES:,}.")
                if not 1 <= hours_budget <= MAX_WALL_SECONDS // 3600:
                    raise ValueError(f"Elapsed hours must be from 1 through {MAX_WALL_SECONDS // 3600}.")
                options = {
                    "endpoint": self.ai_settings.endpoint,
                    "model": self.ai_settings.model,
                    "timeout_seconds": self.ai_settings.timeout_seconds,
                    "model_locality": self.ai_model_locality.value,
                    "max_refinements": round_budget,
                    "max_total_candidates": candidate_budget,
                    "max_wall_seconds": hours_budget * 3600,
                }
                job = self.store.create_job(spec, handler=OVERNIGHT_HANDLER_ID, options=options)
                self._active_job_id = job.id
                dialog.destroy()
                self.ensure_worker()
                self.refresh(select_id=job.id)
            except (ValueError, TypeError, OSError, RuntimeError) as exc:
                messagebox.showerror("Overnight campaign settings", str(exc), parent=dialog)

        tk.Button(actions, text="Start overnight search", command=launch, relief="flat", bg=GREEN, fg="white", activebackground=GREEN_DARK, cursor="hand2", font=("TkDefaultFont", 9, "bold"), padx=13, pady=6).pack(side="right", padx=(0, 7))

    def _selected_job(self):
        selected = self.jobs_table.selection()
        return self._rows_by_iid.get(selected[0]) if selected else None

    def _job_selected(self, _event=None):
        job = self._selected_job()
        if job:
            self._active_job_id = job.id
            self._show_job(job)

    def _candidate_selected(self, _event=None):
        selected = self.candidate_table.selection()
        row = self._candidate_by_iid.get(selected[0]) if selected else None
        self._show_candidate(row)

    def _show_job(self, job):
        selected_candidate = self.candidate_table.selection()
        selected_row = self._candidate_by_iid.get(selected_candidate[0]) if selected_candidate else None
        selected_program = selected_row.get("program") if selected_row else None
        progress = dict(job.progress)
        state = _overnight_state(job)
        search_result = _latest_campaign_result(job) or {}
        display_spec = _latest_campaign_spec(job)
        if job.status in {"queued", "running"}:
            checkpoint_progress = progress.get("candidates_tested", 0)
        else:
            checkpoint_progress = search_result.get("candidates_tested", job.checkpoint.get("examined", 0))
        default_budget = (
            job.options.get("max_total_candidates", job.question.candidate_budget)
            if job.handler == OVERNIGHT_HANDLER_ID else job.question.candidate_budget
        )
        budget = progress.get("candidate_budget") or (job.result or {}).get("effective_candidate_budget") or default_budget
        budget = max(int(budget), 1)
        self.progress.configure(maximum=budget, value=min(int(checkpoint_progress), budget))
        stage = progress.get("stage", "waiting for worker" if job.status == "queued" else "")
        if stage == "preparing scenarios" or "preparing scenarios" in stage:
            stage += f" · scenario {progress.get('scenario_index', 0)}/{progress.get('scenario_count', len(job.question.scenarios))}"
        if job.handler == OVERNIGHT_HANDLER_ID:
            round_number = int(state.get("round_index", 0)) + 1
            stop_reason = ((job.result or {}).get("overnight_campaign") or {}).get("stop_reason")
            extra = f" · {stop_reason.replace('_', ' ')}" if stop_reason else ""
            summary = f"{job.status.upper()} · overnight round {round_number}/{job.options.get('max_refinements', 0) + 1} · {len(display_spec.scenarios)} scenarios · {display_spec.grammar_version}{extra}"
        else:
            summary = f"{job.status.upper()} · {len(job.question.scenarios)} scenarios · {job.question.grammar_version} · question {job.question.fingerprint[:12]}"
        self.job_summary.configure(text=summary)
        self.progress_text.configure(text=f"{stage} · {checkpoint_progress:,}/{budget:,} candidates" if stage or checkpoint_progress else "")
        rows = _candidate_rows(job)
        priority_source = {
            "ranked_candidates": rows,
            "research_memory": search_result.get("research_memory"),
        }
        priority_review = build_research_priority_review(display_spec, priority_source)
        priority_by_program = {
            item["program"]: item for item in (priority_review or {}).get("ranked_candidates", ())
        }
        rows = [
            {**row, "research_priority": priority_by_program.get(row.get("program"))}
            for row in rows
        ]
        rows.sort(key=lambda row: (
            -(row.get("research_priority") or {}).get("priority_score", -1),
            row.get("cost", 0),
            row.get("program", ""),
        ))
        self._candidate_by_iid.clear()
        for iid in self.candidate_table.get_children():
            self.candidate_table.delete(iid)
        for index, row in enumerate(rows):
            iid = f"candidate-{index}"
            self._candidate_by_iid[iid] = row
            self.candidate_table.insert("", "end", iid=iid, values=(
                f"{row.get('matching_scenario_count', 0)}/{row.get('scenario_count', len(display_spec.scenarios))}",
                f"{row['research_priority']['priority_score']}/100" if row.get("research_priority") else "—",
                row.get("cost", "?"),
                row.get("program", ""),
            ), tags=("exact",) if row.get("bijection_on_every_scenario") else ())
        if rows:
            selected_iid = next((iid for iid, row in self._candidate_by_iid.items() if row.get("program") == selected_program), "candidate-0")
            self.candidate_table.selection_set(selected_iid)
            self.candidate_table.focus(selected_iid)
            self._show_candidate(self._candidate_by_iid[selected_iid])
        else:
            self._show_candidate(None)
            checkpoint = job.checkpoint
            saved_result = json.dumps(job.result, ensure_ascii=False, indent=2, sort_keys=True) if job.result else "No result has been saved yet."
            self._set_detail(
                f"Saved specification\n{job.question.canonical_json()}\n\nResult\n{saved_result}\n\nCheckpoint\n{checkpoint or 'No checkpoint yet.'}"
                + (f"\n\nError\n{job.error}" if job.error else "")
            )
        memory = search_result.get("research_memory") or {}
        novelty = memory.get("novelty_counts", {})
        memory_text = ", ".join(f"{key.replace('_', ' ')} {value}" for key, value in sorted(novelty.items()))
        if memory:
            memory_summary = memory_text or "no candidate summary recorded"
            self.memory_label.configure(text=f"Research memory: {memory.get('status', 'unavailable')} · {memory_summary}")
        else:
            self.memory_label.configure(text="Per-round research memory is recorded when each deterministic search finishes.")

    def _show_candidate(self, row):
        self.preview_button.configure(state="normal" if _scenario_map_previews(row) else "disabled")
        self.ask_ai_button.configure(state="normal" if row and self.ai_settings.enabled else "disabled")
        self.proof_plan_button.configure(state="normal" if row else "disabled")
        self.refine_button.configure(state="normal" if _candidate_has_failure(row) else "disabled")
        if not row:
            return
        lines = [row.get("program", ""), f"Cost {row.get('cost', '?')} · matches {row.get('matching_scenario_count', 0)}/{row.get('scenario_count', 0)} scenarios", "Finite result: not a proof."]
        if row.get("finite_family_map_fingerprint"):
            lines.append(
                "Finite-family map fingerprint · "
                + row["finite_family_map_fingerprint"]
                + " · applies only to the searched windows."
            )
        priority = row.get("research_priority")
        if priority:
            lines.append(
                f"\nResearch priority {priority['priority_score']}/100 · {priority['confidence_in_score_inputs']} confidence in score inputs · transparent triage only."
            )
            component_labels = {
                "finite_match_coverage": "match",
                "family_and_offset_breadth": "family/offset breadth",
                "tested_degree_coverage": "degree coverage",
                "program_simplicity": "simplicity",
                "research_memory_novelty": "memory novelty",
            }
            breakdown = []
            for key, label in component_labels.items():
                component = priority["components"][key]
                points = f"{component['points']}/{component['weight']}" if component["available"] else "not available"
                breakdown.append(f"{label}: {points}")
            lines.append("Priority components · " + " · ".join(breakdown))
            lines.extend("Why inspect · " + reason for reason in priority["reasons"])
            lines.extend("Uncertainty · " + note for note in priority["uncertainties"])
        lines.extend(_scenario_evidence_lines(row))
        self._set_detail("\n".join(lines))

    def _ai_settings_label(self):
        if self.ai_settings_error:
            return "Ollama · settings need attention"
        if self.ai_settings.enabled:
            return f"Ollama · {self.ai_settings.model}"
        return "Ollama · Off"

    def configure_ai(self):
        AIAssistantSettingsDialog(
            self.window,
            self.ai_settings,
            self._ai_settings_saved,
            settings_path=self.ai_settings_path,
            model_locality=self.ai_model_locality,
        )

    def design_experiment(self):
        if not self.ai_settings.enabled or not self.ai_settings.model.strip():
            self.configure_ai()
            return
        if self.ai_design_dialog is not None and self.ai_design_dialog.window.winfo_exists():
            self.ai_design_dialog.window.lift()
            return
        self.ai_design_dialog = AIExperimentDesignerDialog(
            self.window,
            self.ai_settings,
            self._ai_settings_saved,
            self._experiment_design_accepted,
            settings_path=self.ai_settings_path,
            model_locality=self.ai_model_locality,
        )

    def _experiment_design_accepted(self, design, provenance):
        if design.spec is None:
            return
        for name, value in design.form_values.items():
            getattr(self, name).set(value)
        self._pending_experiment_design = (design, provenance)
        is_refinement = isinstance(provenance.get("refinement"), dict)
        self.form_note.configure(
            text=(
                f"Unverified AI {'refinement' if is_refinement else 'design'} applied: {design.title}. "
                + ("It retains exact parent failure evidence. " if is_refinement else "")
                + "Review or edit the controls, then press Start campaign to run the deterministic search."
            ),
            fg=AMBER,
        )

    def _ai_settings_saved(self, settings, model_locality=ProviderLocality.UNKNOWN):
        self.ai_settings = settings
        self.ai_model_locality = ProviderLocality(model_locality)
        self.ai_settings_error = None
        self.ai_settings_button.configure(text=self._ai_settings_label())
        selected = self.candidate_table.selection()
        row = self._candidate_by_iid.get(selected[0]) if selected else None
        self.ask_ai_button.configure(state="normal" if row and settings.enabled else "disabled")
        self.refine_button.configure(state="normal" if _candidate_has_failure(row) else "disabled")

    def refine_selected(self):
        job = self._selected_job()
        selected = self.candidate_table.selection()
        row = self._candidate_by_iid.get(selected[0]) if selected else None
        if not job or not row or not _candidate_has_failure(row):
            return
        if not self.ai_settings.enabled or not self.ai_settings.model.strip():
            self.configure_ai()
            return
        spec = _latest_campaign_spec(job)
        try:
            context = build_refinement_context(
                parent_job_id=job.id,
                prior_specification=json.loads(spec.canonical_json()),
                prior_specification_fingerprint=spec.fingerprint,
                candidate=row,
            )
        except (TypeError, ValueError, KeyError) as exc:
            messagebox.showerror("Counterexample context", str(exc), parent=self.window)
            return
        self.ai_design_dialog = AIExperimentDesignerDialog(
            self.window,
            self.ai_settings,
            self._ai_settings_saved,
            self._experiment_design_accepted,
            refinement_context=context,
            settings_path=self.ai_settings_path,
            model_locality=self.ai_model_locality,
        )

    def ask_about_candidate(self):
        job = self._selected_job()
        selected = self.candidate_table.selection()
        row = self._candidate_by_iid.get(selected[0]) if selected else None
        if not job or not row:
            return
        if not self.ai_settings.enabled:
            self.configure_ai()
            return
        try:
            evidence = build_candidate_evidence(SimpleNamespace(question=_latest_campaign_spec(job)), row)
        except (TypeError, ValueError, KeyError) as exc:
            messagebox.showerror("Candidate context", str(exc), parent=self.window)
            return
        self.ai_dialog = AIExplanationDialog(
            self.window,
            self.ai_settings,
            evidence,
            self._ai_settings_saved,
            on_review_saved=lambda review: self._save_ai_review(job.id, review),
            settings_path=self.ai_settings_path,
            model_locality=self.ai_model_locality,
        )

    def plan_proof_selected(self):
        job = self._selected_job()
        selected = self.candidate_table.selection()
        row = self._candidate_by_iid.get(selected[0]) if selected else None
        if not job or not row:
            return
        if not self.ai_settings.enabled or not self.ai_settings.model.strip():
            self.configure_ai()
            return
        try:
            evidence = build_candidate_evidence(SimpleNamespace(question=_latest_campaign_spec(job)), row)
            search_result = _latest_campaign_result(job) or {}
            obligations = (
                search_result.get("proof_obligations")
                or (job.result or {}).get("proof_obligations")
                or (
                    "prove the map is defined on every source object in the stated class",
                    "prove target membership, injectivity, and surjectivity or give a valid inverse",
                    "prove the degree offset for every input size",
                )
            )
            context = build_proof_assistance_context(evidence, obligations)
        except (TypeError, ValueError, KeyError) as exc:
            messagebox.showerror("Proof-plan context", str(exc), parent=self.window)
            return
        self.ai_proof_dialog = AIProofPlanDialog(
            self.window,
            self.ai_settings,
            context,
            self._ai_settings_saved,
            on_review_saved=lambda review: self._save_ai_review(job.id, review),
            settings_path=self.ai_settings_path,
            model_locality=self.ai_model_locality,
        )

    def _save_ai_review(self, job_id, review):
        try:
            self.store.record_assistant_review(job_id, review)
        except (OSError, ValueError, KeyError, sqlite3.Error):
            return "the response could not be saved locally with this campaign"
        return None

    def _set_detail(self, value):
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", value)
        self.detail.configure(state="disabled")

    def preview_selected(self):
        selected = self.candidate_table.selection()
        row = self._candidate_by_iid.get(selected[0]) if selected else None
        previews = _scenario_map_previews(row)
        if previews:
            preview = previews[0]["example_map"]
            scenario_index = previews[0].get("scenario_index")
            scenario_label = scenario_index + 1 if isinstance(scenario_index, int) else 1
            title = f"{row.get('program', 'Generated candidate')} · scenario {scenario_label}"
            self.on_preview(preview, title)
            self.parent.bell()

    def export_selected(self):
        job = self._selected_job()
        if not job:
            messagebox.showinfo("Select a campaign", "Choose a saved campaign to export its research dossier.", parent=self.window)
            return
        path = filedialog.asksaveasfilename(
            parent=self.window,
            title="Export research dossier",
            defaultextension=".json",
            initialfile=f"ascent-research-dossier-{job.id[:8]}.json",
            filetypes=(("Research dossier JSON", "*.json"), ("All files", "*")),
        )
        if not path:
            return
        try:
            assistant_reviews = self.store.assistant_reviews(job.id)
            dossier = build_research_dossier(
                job,
                events=self.store.events(job.id),
                assistant_reviews=assistant_reviews,
            )
            destination = write_dossier(path, dossier)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Dossier export failed", str(exc), parent=self.window)
            return
        review_count = len(assistant_reviews)
        review_note = f"\nIncluded {review_count} saved assistant review{'s' if review_count != 1 else ''}." if review_count else ""
        messagebox.showinfo("Dossier exported", f"Saved the reproducible finite research dossier to:\n{destination}{review_note}", parent=self.window)

    def _control_selected(self, action):
        job = self._selected_job()
        if not job:
            return
        try:
            if action == "pause" and job.status in {"queued", "running"}:
                self.store.request_pause(job.id)
            elif action == "cancel" and job.status in {"queued", "running"}:
                self.store.request_cancel(job.id)
            elif action == "resume" and job.status in {"paused", "interrupted", "failed"}:
                self.store.resume_job(job.id)
                self.ensure_worker()
            self.refresh(select_id=job.id)
        except (ValueError, KeyError, OSError, RuntimeError) as exc:
            messagebox.showerror("Campaign control", str(exc), parent=self.window)

    def pause_selected(self):
        self._control_selected("pause")

    def resume_selected(self):
        self._control_selected("resume")

    def cancel_selected(self):
        self._control_selected("cancel")

    def show_checkpoint(self):
        job = self._selected_job()
        if not job:
            return
        dialog = tk.Toplevel(self.window)
        dialog.title(f"Campaign checkpoint · {job.id[:8]}")
        dialog.geometry("760x520")
        dialog.configure(bg=BG)
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(1, weight=1)
        summary = {
            "job_id": job.id,
            "status": job.status,
            "question_fingerprint": job.question.fingerprint,
            "progress": job.progress,
            "checkpoint": job.checkpoint,
            "error": job.error,
        }
        tk.Label(dialog, text="Durable saved state", bg=BG, fg=INK, font=("TkDefaultFont", 14, "bold")).grid(row=0, column=0, sticky="w", padx=14, pady=12)
        text = tk.Text(dialog, wrap="none", bg=PANEL, fg=INK, relief="flat", font=("TkFixedFont", 9), padx=10, pady=8)
        text.grid(row=1, column=0, sticky="nsew", padx=(14, 0), pady=(0, 14))
        scroll = ttk.Scrollbar(dialog, orient="vertical", command=text.yview)
        scroll.grid(row=1, column=1, sticky="ns", padx=(0, 14), pady=(0, 14))
        text.configure(yscrollcommand=scroll.set)
        text.insert("1.0", json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        text.configure(state="disabled")

    def refresh(self, select_id=None):
        try:
            jobs = tuple(job for job in self.store.list_jobs(limit=500) if job.handler in CAMPAIGN_HANDLERS)
        except OSError as exc:
            self.job_summary.configure(text=f"Cannot read saved campaigns: {exc}")
            return
        previous = select_id or self._active_job_id
        existing = set(self.jobs_table.get_children())
        self._rows_by_iid = {}
        desired = set()
        for job in jobs:
            iid = f"job-{job.id}"
            desired.add(iid)
            self._rows_by_iid[iid] = job
            progress = job.progress.get("candidates_tested", job.checkpoint.get("examined", 0))
            stage = job.progress.get("stage", "")
            kind = "Overnight · " if job.handler == OVERNIGHT_HANDLER_ID else ""
            label = f"{kind}{job.question.scenarios[0].source.family} → {job.question.scenarios[0].target.family} · {job.id[:8]}"
            values = (job.status, f"{progress:,} tested")
            if iid in existing:
                self.jobs_table.item(iid, text=label, values=values)
            else:
                self.jobs_table.insert("", "end", iid=iid, text=label, values=values)
            self.jobs_table.item(iid, tags=("running",) if job.status == "running" else ())
        for iid in existing - desired:
            self.jobs_table.delete(iid)
        self.jobs_table.tag_configure("running", foreground=GREEN_DARK)
        if previous:
            iid = f"job-{previous}"
            if iid in desired:
                self.jobs_table.selection_set(iid)
                self.jobs_table.focus(iid)
                self._active_job_id = previous
                self._show_job(self._rows_by_iid[iid])

    def _schedule_refresh(self):
        if not self.window.winfo_exists():
            return
        selected = self._selected_job()
        self.refresh(select_id=selected.id if selected else self._active_job_id)
        self.window.after(900, self._schedule_refresh)
