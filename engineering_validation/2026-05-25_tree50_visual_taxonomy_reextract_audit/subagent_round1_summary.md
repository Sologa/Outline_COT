# Subagent Round 1 Summary

Date: 2026-05-25

Scope: the 15 papers identified by manual QA as requiring taxonomy re-extraction
from source figures.

## Completion

- Manual draft files created: 15 / 15
- Existing v2 payloads modified: 0
- Current drafts are candidate source-grounded reconstructions, not promoted
  replacement payloads.

## Per-Paper Draft Status

| paper_id | draft_status | key correction |
|---|---|---|
| 1703.06118 | strict_tree | Completed Figure 2 leaves, then added Figure 4 method refinement and Figure 3 dimensions auxiliary facet. |
| 1805.10511 | strict_tree | Completed the HUIM taxonomy siblings and lower leaves from Figure 2. |
| 1910.04656 | strict_tree | Completed Figure 1 beyond the top layer. |
| 1910.08252 | strict_tree | Recovered Figures 3 and 4 under the prose-level technical-features root after original failure. |
| 2001.09957 | multifaceted_forest | Added Figures 4-6 and reference leaves beyond the Figure 3-only v2 draft. |
| 2006.00093 | multifaceted_forest | Recovered raster PNG trees after original failure. |
| 2008.07235 | outline_like_taxonomy | Marked as outline-like and added the omitted parallel branches. |
| 2009.12153 | strict_tree | Restored the full Figure 5 `\Tree[...]`, including sibling branches. |
| 2010.00713 | strict_tree | Completed Figure 1 down to lower layers. |
| 2010.12742 | strict_tree | Replaced the wrong Figure 1 interpretation with the actual tree. |
| 2011.04406 | strict_tree | Completed deeper Figure 2 levels. |
| 2011.04843 | outline_like_taxonomy | Marked as outline-like and replaced unrelated v2 content with source figure content. |
| 2011.08641 | strict_tree | Completed Figure 7 sibling branch and missing children. |
| 2012.09276 | strict_tree | Completed Figure 1 beyond the second layer. |
| 2103.00111 | strict_tree | Completed Figure 2 beyond the second layer. |

## Pipeline Implications

- The dominant failure is not a final payload formatting problem. The worker
  often did not receive or parse the actual figure pixels/vector text deeply
  enough to enumerate all visible leaves.
- Raster-only and EPS/PDF figure assets need a dedicated visual extraction
  lane, not only text/caption/context extraction.
- Validation needs a completeness check against candidate figure trees. The old
  countability threshold is too weak because a shallow partial tree can pass.
- Multi-figure papers must be represented as a forest when the paper supplies
  several taxonomy facets.

## Next Promotion Gate

Before replacing any v2 payload, each draft should be checked once more against
the rendered figure image or TeX tree source and normalized into the target
payload schema with explicit figure-level provenance.
