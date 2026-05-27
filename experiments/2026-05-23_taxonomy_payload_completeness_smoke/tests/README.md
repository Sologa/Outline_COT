# Tests

The experiment-local validation is currently embedded in `prototype/run_payload_completeness_smoke.py`.

Required smoke checks:

- script compiles with `python3 -m py_compile`
- default render produces two paper-096 prompt arms
- batch input contains two requests
- structural payload contains all original taxonomy nodes and structural edges
- rendered taxonomy payload files do not contain excluded evidence, audit, classified-item, rejected-candidate, source-pack, or local-path fields
