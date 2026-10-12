"""Guard DOM event targets expected by the public browser workbench.

These static controls were omitted during a GUI refactor, aborting app.js
initialization and breaking subsequent experiment controls.
"""
from importlib.resources import files
import re

STATIC = files("ac.gui.static")


def test_static_direct_event_targets_exist_in_html():
    html = STATIC.joinpath("index.html").read_text(encoding="utf-8")
    js = STATIC.joinpath("app.js").read_text(encoding="utf-8")
    direct = set(re.findall(r"\$\('#([A-Za-z0-9_-]+)'\)\.addEventListener", js))
    # Both controls below are inserted into innerHTML immediately before binding.
    dynamic = {"learn-open-inspector", "browser-apply"}
    missing = sorted(id_ for id_ in direct - dynamic if f'id="{id_}"' not in html)
    assert not missing, f"Missing static DOM event targets: {missing}"


def test_saved_experiment_persistence_dom_exists():
    html = STATIC.joinpath("index.html").read_text(encoding="utf-8")
    for id_ in ("save-experiment", "export-experiment", "import-experiment",
                "saved-experiment-count", "saved-experiment-list",
                "saved-experiments-feedback"):
        assert f'id="{id_}"' in html
