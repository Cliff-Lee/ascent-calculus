# AM-AI data flow and privacy

AM-AI is opt-in. Deterministic search works without configuring a model. The
application does not launch Ollama, download models, run model-generated code,
or send AM-AI telemetry as part of these research workflows.

## What leaves the machine

Without an explicit assistant action, no AI request is made. The benchmark
runner is offline by default; its `--with-ai` flag is the explicit opt-in.
Ollama connections are limited to a loopback HTTP origin and redirects and
proxy routing are disabled by the adapter.

When an assistant request is made, its prompt can include the selected class
and pattern definitions, degree and offset windows, transformation grammar and
budgets, bounded candidate summaries, and exact finite counterexamples. The
overnight campaign can include the current specification and failed scenario
in its refinement request. It does not read arbitrary files or include the
research database wholesale. A loopback endpoint only describes the path to
Ollama; a selected cloud model may send the prompt to remote inference. The UI
and benchmark record retain the model locality as local, remote, or unknown.
The command-line benchmark records this as a caller-declared value; leave it
unknown unless the selected model's locality has been checked in Ollama.

## What is stored

The local AI settings file stores the enabled flag, loopback endpoint, model
name, and timeout. It stores no API key or credential. The exact assistant
request, response, selected model, validation status, and finite evidence can
be retained in the SQLite job database and research dossier. A dossier export
therefore may contain unpublished mathematical ideas and counterexamples;
researchers should review it before sharing. These local files are not
encrypted by Ascent Calculus.

Assistant content remains explicitly unverified. The deterministic engine
checks every proposed follow-up search, and AI text cannot change a result's
proof status.

## AM-AI10a audit

The offline benchmark path runs only the deterministic transformation-family
worker and labels its result `offline_deterministic_baseline`. Its tests replace
Ollama construction with a failure sentinel to verify that this path does not
instantiate a provider. The paired path runs the same root question and total
candidate cap through a deterministic baseline and an AI-guided campaign. The
baseline spends the cap on its root search; the guided campaign can spend its
initial per-specification cap on the root and use the remainder on a validated
follow-up. The record includes both finite results, budgets, model locality,
timings, and additional program/scenario matches. This is a bounded comparison
protocol, not a claim that model guidance is generally more effective. The
standalone runner is a bounded foreground benchmark; the desktop overnight
workflow remains the SQLite-checkpointed option for unattended and resumable
searches. It reports the search engine's total exact-match counts separately
from its retained candidate details, so the pairwise comparison is not
misrepresented as exhaustive when the candidate list is truncated.

The loopback transport restriction and opt-in path were tested offline with
mocked HTTP/provider behavior. A live Ollama request, model-locality review,
and Linux desktop review remain target-machine checks.
