# Subagent Reading Summary

Subagent: `019e50a2-4793-7411-8069-8b6b07fc06de`  
Mode: read-only report review  
Reviewed file: `taxonomy_extraction_audit_report_for_codex.md`

| paper_id | report decision | extractable structure | structure type | evidence strength | recommended route |
|---|---|---|---|---|---|
| `002_2404.03282` | `explicit` | Patient-transport five-field notation: `alpha | beta | gamma | delta | epsilon`, plus Table 3 field values and Table 4 publication-to-field mapping. | Faceted taxonomy, not a tree. | High; supported by prose, Table 3, and Table 4. | Full manual extraction. |
| `055_2402.00462` | `taxonomy_like` | Data-management aspects, study-aspect mapping, challenge groups, impact, solution/status/reference mapping. | Faceted / typed graph, not a single tree. | Medium; table evidence is present, but complete semantics of the 11 aspects may need the replication package. | Ambiguous review or scoped full manual extraction. |
| `084_2501.18845` | `explicit` | Four LLM text data augmentation categories, Figure 4 detailed method taxonomy, Figure 3 prompt/retrieval axes, Table I aspects, and Table II granularity. | Taxonomy-like DAG with hybrid cross-listing. | High; supported by Figure 4, Tables I-II, and explicit prose. | Highest-priority full manual extraction. |

## Key Judgments

- `084_2501.18845` is the strongest candidate. Full extraction should preserve
  DAG/cross-listing and avoid forcing hybrid methods into a single tree. The
  report notes that `KAPING` appears twice and should be preserved as a
  source-observed duplication until author/source intent is checked.
- `002_2404.03282` is stable and extractable. The main production issue is not
  whether it is a taxonomy, but exact transcription of rotated, math-heavy
  Table 4 notation and subscripts.
- `055_2402.00462` is useful but boundary-sensitive. It is better treated as an
  SLR coding / challenge-solution mapping unless the experiment explicitly
  accepts taxonomy-like faceted structures.

## Rule-Risk Notes

- Do not extract whole outlines.
- Do not rely on section headings alone.
- Preserve facet/table relations:
  - `002`: five-field facet structure.
  - `055`: aspect/challenge/solution/status/reference typed relations.
  - `084`: Figure 4 hierarchy plus hybrid cross-links and Table I/II multi-label facets.
- Do not compress faceted or DAG-like structures into a single parent-child tree.
