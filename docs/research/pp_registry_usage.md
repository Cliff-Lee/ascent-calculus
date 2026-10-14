# Offline Research Library

This tool imports research leads, not verified theorems. Use Python >=3.11. From a source checkout set `PYTHONPATH=.`; installed packages expose `ac-research-library` with the same arguments as the module invocation.

```sh
mkdir -p .local-imports/pp-ri
python -m ac.research_library --database .local-imports/pp-ri/registry.sqlite3 ingest /path/to/ascent_calculus_permutation_patterns_research_pack.zip --expected-sha256 d254e7db1b3ca4cea306d0a295db0128ec3dbdde426c3e36f97619bc971d7bd7
python -m ac.research_library --database .local-imports/pp-ri/registry.sqlite3 search --priority P0 --method bijection
python -m ac.research_library --database .local-imports/pp-ri/registry.sqlite3 search --family inversion_sequences --year 2026
python -m ac.research_library --database .local-imports/pp-ri/registry.sqlite3 search --author Claesson --source-type 'conference talk' --verification-status CATALOGUED
python -m ac.research_library --database .local-imports/pp-ri/registry.sqlite3 search --format csv
```

The database argument is mandatory to avoid silently opening or modifying user application data. Parent directories must exist. Import twice preserves the timestamp and database bytes and returns `already_ingested`. Additional versions retain all older source fields. Search is bounded (default 200, maximum 1000 rows); narrow by pack and use explicit limits when exporting multiple versions.

```python
from ac.research_library import Catalogue, ingest_pack
result = ingest_pack('research_pack.zip', 'registry.sqlite3')
registry = Catalogue('registry.sqlite3')
leads = registry.search(method='generating', family='trees', priority='P0')
original_metadata = registry.metadata(result['pack_sha256'])
exact_bytes = registry.source(result['pack_sha256'])
json_text = registry.export(pack=result['pack_sha256'])
csv_text = registry.export(format='csv', author='Pudwell')
```

Returned dictionaries are detached copies. No API mutates source records, promotes claims, fetches URLs, runs constructions or certifies novelty. Family indexes are heuristic; original metadata remains available for interpretation. Association year may differ from publication year.

Run deterministic offline tests without a ZIP download:

```sh
PP_RESEARCH_PACK=/path/that/does/not/exist python -m pytest tests/test_pp_research_library.py -o addopts='' -q
```

To repeat the real-pack acceptance run, provide `PP_RESEARCH_PACK=/absolute/path/to/the/supplied.zip`. The pack is read-only. All databases use test temporary directories.
