# Root Cause For Prior Tree Errors

The prior manual re-extraction rounds treated `pdftotext -layout` and OCR output as if spatial alignment encoded parent-child topology. This is false for rendered taxonomy figures with curved arrows, shared child lists, DAG-like links, or multi-parent visual encodings.

Confirmed example: `2308.13420` Figure 4. `pdftotext -layout` places `Algorithm selection        Adaptive crossover`, `Operator selection        Adaptive mutation`, and `Sub-population selection   Adaptive local search` on aligned rows. The rendered figure and paper prose show the three adaptive operations are all children of `Operator selection`.

New rule: `pdftotext` and OCR are node-label inventory only. Edges must be verified from one of: TeX/forest/TikZ source edge structure, rendered figure arrow tracing, or explicit prose that names the parent-child relation.
