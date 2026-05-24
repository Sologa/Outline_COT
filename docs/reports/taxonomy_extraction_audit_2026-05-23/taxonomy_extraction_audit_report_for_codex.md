# Taxonomy Extraction Audit Report

Prepared for: Codex / taxonomy-extraction pipeline review  
Audit target: determine whether three arXiv survey/review papers contain extractable taxonomy structures.  
Audit mode: PDF/text evidence only; section headings alone were not treated as taxonomy evidence.

## Source Papers

| paper_id | title | arXiv abs | PDF |
|---|---|---|---|
| 002_2404.03282 | Patient Transport in Hospitals: A Literature Review of Operations Research and Management Science Methods | https://arxiv.org/abs/2404.03282 | https://arxiv.org/pdf/2404.03282.pdf |
| 055_2402.00462 | Exploring Data Management Challenges and Solutions in Agile Software Development: A Literature Review and Practitioner Survey | https://arxiv.org/abs/2402.00462 | https://arxiv.org/pdf/2402.00462.pdf |
| 084_2501.18845 | Text Data Augmentation for Large Language Models: A Comprehensive Survey of Methods, Challenges, and Opportunities | https://arxiv.org/abs/2501.18845 | https://arxiv.org/pdf/2501.18845.pdf |

## Audit Rules Applied

Do not extract the paper outline. Do not treat section headings alone as taxonomy. Extract only structures supported by rendered figures, table bodies, captions plus table/figure body, or surrounding prose that explicitly defines categories, classes, facets, or classification fields. Reject ordinary experimental classification tasks, dataset labels, performance tables, and review-process diagrams. Preserve faceted or table-like structures as facets and mappings rather than forcing them into a single tree.

## Executive Summary

| paper_id | taxonomy_status | taxonomy_kind | confidence | one-sentence reason | extraction_priority |
|---|---:|---:|---:|---|---:|
| 002_2404.03282 | explicit | faceted_taxonomy | high | The paper explicitly defines a five-field notation `alpha | beta | gamma | delta | epsilon` for classifying patient-transport problem variants and then applies it to reviewed publications. | 2 |
| 055_2402.00462 | taxonomy_like | faceted_taxonomy | medium | The paper does not call the structure a taxonomy, but it classifies studies by data-management aspects and maps challenge groups to solutions, status, and references. | 3 |
| 084_2501.18845 | explicit | taxonomy_like_dag | high | The paper explicitly classifies text data augmentation into four technique categories and provides a detailed method tree plus aspect and granularity facets. | 1 |

## Status Definitions Used

| status | meaning in this audit |
|---|---|
| explicit | The paper itself explicitly introduces a taxonomy, classification system, typology, notation, or category system. |
| taxonomy_like | The paper provides a stable category/mapping structure suitable for extraction, but does not clearly label it as a formal taxonomy. |
| none_found | No real extractable taxonomy-like structure was found after checking figures/tables/prose. |
| ambiguous | Some structure may exist, but evidence is insufficient or unreadable. |
| blocked | Extraction decision cannot be made because the necessary figure/table/body is inaccessible or unreadable. |

---

# Per-Paper Analysis

## 002_2404.03282 — Patient Transport in Hospitals: A Literature Review of Operations Research and Management Science Methods

### 1. Decision

| field | value |
|---|---|
| taxonomy_status | explicit |
| taxonomy_kind | faceted_taxonomy |
| worth full manual extraction | yes |
| confidence | high |

This paper is a strong extraction candidate. The primary extractable structure is the five-field notation for patient-transport problem variants. It is not merely an outline: the authors define fields, values, semantics, and then classify reviewed papers using those fields.

### 2. Evidence Checked

| locator | evidence checked | audit note |
|---|---|---|
| PDF printed p. 10 / parser P9, Section 3.2 | Surrounding prose introducing `alpha | beta | gamma | delta | epsilon` | The prose explicitly says the notation classifies patient-transport problems and names the five fields. |
| PDF printed p. 11 / parser P10, Table 3 | Rendered table body and caption | Table body defines all field values for fleet, depot, constraints, objectives, and uncertainty. |
| PDF printed p. 12–14 / parser P11–P13, Sections 3.2.3–3.2.5 | Surrounding explanatory prose | Provides semantics for capacity, equipment, priority, skill, isolation, time windows, objectives, and uncertainty. |
| PDF printed p. 16 / parser P15, Table 4 | Rendered rotated table body and caption | Table 4 maps reviewed publications to the five fields. |
| PDF printed p. 16–19 / parser P16–P19, Figures 2–4 and prose | Distribution charts derived from the notation | Useful supporting analysis, but not the primary taxonomy. |

### 3. Extracted Candidate Taxonomy

Recommended representation: keep this as a faceted taxonomy. Do not coerce into a single parent-child tree, because each paper/problem instance receives one value set per field.

#### Facet `alpha` — Fleet characteristics

| code | meaning |
|---|---|
| `F_MULT` | multiple vehicle types |
| `F_N` | N vehicle types |
| `F_1` | single vehicle type |
| `F_empty` / `F_∅` | vehicle-free |

#### Facet `beta` — Depot characteristics

| code | meaning |
|---|---|
| `D_MULT` | multiple depots |
| `D_N` | N depots |
| `D_1` | single depot |
| `D_empty` / `D_∅` | no depots |

#### Facet `gamma` — Constraints

| constraint group | code | meaning |
|---|---|---|
| Capacity | `CAP_1` | unit capacity |
| Capacity | `CAP_UNIF` | uniform capacity |
| Capacity | `CAP_MULT` | multiple capacity classes / multi-capacity |
| Equipment | `EQ` | additional equipment |
| Priority | `PRIO` | priority levels |
| Skill | `SK` | skill requirements |
| Isolation | `ISO` | isolated transports |
| Time windows | `TW_HARD` | hard time windows |
| Time windows | `TW_SOFT` | soft time windows |
| Time windows | `TW_MIX` | mixed time windows |
| Time | `T_S` | staff time |
| Time | `T_L` | loading time |
| Time | `T_TT` | travel-time constraints |

#### Facet `delta` — Problem objective(s)

| objective group | code | meaning |
|---|---|---|
| Cost | `C` | cost |
| Waiting time | `WT_V` | vehicle waiting time |
| Waiting time | `WT_P` | patient waiting time |
| Travel time | `TT_V` | vehicle travel time |
| Travel time | `TT_P` | patient travel time |
| Travel time | `TT_E` | empty travel time |
| Ergonomic burden | `max B` | maximum ergonomic burden |
| Flow time | `sum w_j F_j` | total weighted flow time |

#### Facet `epsilon` — Uncertainty

| code | meaning |
|---|---|
| `R` | uncertain requests |
| `TT` | uncertain travel times |

#### Candidate classification mapping from Table 4

Treat this table as candidate extraction output. The table is rotated and math-heavy; production extraction should verify exact subscripts from the PDF or TeX source.

| publication | alpha | beta | gamma | delta | epsilon | confidence note |
|---|---|---|---|---|---|---|
| Nickel et al. [3] | `F_∅` | `D_1` | `CAP_1; PRIO` | `C; TT_E` | `R` | high |
| Kallrath [4] | `F_MULT` | `D_MULT` | `CAP_MULT; EQ; ISO; TW_SOFT; T_TT` | `C + WT_V,P + TT_V,P` | `R` | high |
| Melachrinoudis et al. [5] | `F_MULT` | `D_MULT` | `CAP_MULT; TW_SOFT` | `C + WT_P + TT_P` | none visible | high |
| Fiegl et al. [6] | `F_∅` | `D_∅` | `CAP_MULT; PRIO; TW_SOFT` | `sum w_j F_j` | `R` | high |
| Hanne et al. [7] | `F_MULT` | `D_MULT` | `CAP_MULT; EQ; ISO; T_S,L,TT` | `C + WT_V,P + TT_V,P` | `R; TT` | high |
| Beaudry et al. [8] | `F_MULT` | `D_MULT` | `CAP_MULT; EQ; PRIO; SK; ISO; TW_MIX; T_S,L,TT` | `C + WT_V,P + TT_V,P,E` | `R; TT` | high |
| Kergosien et al. [9] | `F_MULT` | `D_MULT` | `CAP_1; EQ; PRIO; ISO; TW_HARD; T_S` | `C` | `R` | high |
| Turan et al. [10] | `F_∅` | `D_MULT` | `CAP_1; PRIO; TW_MIX; T_L` | `C + WT_V,P + TT_V,E` | none visible | high |
| Kergosien et al. [11] | `F_1` | `D_MULT` | `CAP_1; PRIO; TW_MIX; T_S` | `C; WT_P; TT_E` | `R` | high |
| Schmid et al. [12] | `F_∅` | `D_MULT` | `CAP_1; TW_MIX` | `C + WT_V,P + TT_E` | none visible | high |
| von Elmbach et al. [13] | `F_∅` | `D_MULT` | `CAP_1; PRIO; TW_MIX` | `max B` | none visible | high |
| Zhang et al. [14] | `F_1` | `D_MULT` | `CAP_MULT; SK; TW_HARD; T_S,L,TT` | `C + WT_V,P + TT_V,P` | none visible | high |
| Detti et al. [15] | `F_MULT` | `D_MULT` | `CAP_MULT; ISO; TW_MIX; T_L,TT` | `C + WT_V,P + TT_V,P,E` | none visible | high |
| Vancroonenburg et al. [16] | `F_∅` | `D_MULT` | `CAP_1; SK; TW_MIX; T_S` | `TT_V` | `R` | high |
| Séguin et al. [17] | `F_∅` | `D_∅` | `T_S` | `C` | none visible | high |
| von Elmbach et al. [18] | `F_∅` | `D_MULT` | `CAP_1; TW_SOFT; T_L` | `max B` | none visible | high |
| Van den Berg et al. [19] | `F_MULT` | `D_MULT` | `CAP_1; PRIO; SK; TW_MIX; T_S` | `TT_V` | `R; TT` | high |
| Xiao et al. [20] | `F_∅` | `D_∅` | `CAP_1; TW_SOFT` | `WT_P + TT_P` | none visible | high |
| Nasira et al. [21] | `F_1` | `D_1` | `CAP_MULT; TW_SOFT; T_L` | `C + WT_V,P + TT_V,P,E` | none visible | high |
| Maka et al. [22] | `F_∅` | `D_MULT` | `CAP_1; TW_HARD; T_S,L,TT` | `C + WT_P + TT_V,P` | none visible | high |
| Kergosien et al. [23] | `F_1` | `D_1` | `CAP_1; SK; TW_SOFT; T_S,L` | `C + TT_V` | `R` | high |
| Bärmann et al. [24] | `F_∅` | `D_∅` | `CAP_1; PRIO; SK; ISO; TW_MIX; T_S` | `TT_E` | `R` | high |

### 4. Evidence Ledger

| evidence_id | locator | compact transcription / paraphrase | supports |
|---|---|---|---|
| P1-E1 | PDF p. 10, Section 3.2 | Introduces five-field notation for classifying patient-transport problem variants. | Explicit taxonomy decision. |
| P1-E2 | PDF p. 11, Table 3 | Fields visible: fleet, depot, constraints, objectives, uncertainty. | Facet inventory. |
| P1-E3 | PDF p. 12–14, Sections 3.2.3–3.2.5 | Prose defines constraints, objective codes, and uncertainty codes. | Category semantics. |
| P1-E4 | PDF p. 16, Table 4 | Publication rows are assigned values in `alpha`, `beta`, `gamma`, `delta`, `epsilon`. | Operationalized classification mapping. |

### 5. Rejected Candidates

| candidate | reason for rejection |
|---|---|
| Figure 1 PRISMA flow diagram | Review-process flow, not a taxonomy of the domain. |
| Table 1 search terms | Search-query construction, not a domain classification system. |
| Table 2 identified papers | Bibliographic list; not taxonomy. |
| Figures 2–4 distribution charts | Useful derived summaries, but the extractable taxonomy is Table 3/Table 4. Extract distributions only as secondary statistics if needed. |
| Section headings | Not extracted unless backed by Table 3/Table 4 or explicit prose. |

### 6. Open Questions / Blockers

No blocker for audit. For production, verify exact TeX math symbols/subscripts because Table 4 is rotated and dense. The extraction target is reliable, but exact rendering such as `T_S,L,TT`, `WT_V,P`, and `TT_V,P,E` should be normalized consistently.

---

## 055_2402.00462 — Exploring Data Management Challenges and Solutions in Agile Software Development: A Literature Review and Practitioner Survey

### 1. Decision

| field | value |
|---|---|
| taxonomy_status | taxonomy_like |
| taxonomy_kind | faceted_taxonomy |
| worth full manual extraction | yes, with scope control |
| confidence | medium |

This paper contains extractable taxonomy-like structures, but not a formal single-tree taxonomy. The best extraction target is a faceted SLR coding scheme: data-management aspects, study references, overlapping aspect membership, challenge groups, impact levels, solution entries, implementation/proposal status, and references.

### 2. Evidence Checked

| locator | evidence checked | audit note |
|---|---|---|
| PDF printed p. 12 / parser P11, Section 3.2.1 | Definitions of four top data-management aspects | Data Integration, Data Collection, Data Quality, and Data Analysis receive prose definitions. |
| PDF printed p. 13 / parser P12, Figure 2 | Rendered bar chart | Shows distribution of studies across fifteen data-management aspects. |
| PDF printed p. 14 / parser P13, Table 1 | Rendered rotated table body | Lists fifteen data-management aspects and references. |
| PDF printed p. 15 / parser P14, Figure 3 | Rendered overlap diagram | Shows multi-label overlap among Data Collection, Data Integration, Data Analysis, and Data Quality. |
| PDF printed p. 17 / parser P16, Table 2 | Rendered table body | Groups prioritized challenges under four aspect headings with study counts and impact levels. |
| PDF printed p. 17 / parser P16, Table 3 | Rendered table body | Maps Data Integration challenges to solutions, status, and references. |
| PDF printed p. 23 / parser P22, Table 4 | Rendered table body | Maps Data Collection challenges to solutions, status, and references. |
| PDF printed p. 27 / parser P26, Table 5 | Rendered table body | Maps Data Quality challenges to solutions, implementation status, and references. |
| PDF printed p. 30 / parser P29, Table 6 | Rendered table body | Maps Data Analysis challenges to solutions, status, and references. |
| PDF printed p. 32–33 / parser P31–P32, Figure 4 | Caption/prose checked | Summary figure exists, but extracted content is better supported by Tables 2–6. |

### 3. Extracted Candidate Taxonomy

Recommended representation: faceted taxonomy / typed graph. Do not force into one tree. A study can belong to multiple aspects; a challenge maps to multiple solutions; a solution has status and reference attributes.

#### Facet A — Data-management aspect inventory from Table 1

1. Data Integration
2. Data Storage
3. Data Validation and Governance
4. Data Quality
5. Data Ingestion
6. Data Collection
7. Data Security and Compliance
8. Data Privacy
9. Data Analysis
10. Data Visualization
11. Data-Driven Decision Making
12. Data-Driven Development
13. Data Testing
14. Data Maintenance Strategy
15. Data Management Development

#### Facet B — Four top aspects defined in the PDF

| aspect | definition summary |
|---|---|
| Data Integration | Combining data from multiple sources/systems into a unified consistent view for analysis, reporting, and decisions. |
| Data Collection | Gathering information for later analysis and decision-making. |
| Data Quality | Accuracy, completeness, and consistency of a dataset. |
| Data Analysis | Inspection, cleaning, transformation, and modeling of data to derive insights and support decisions. |

#### Facet C — Study-count distribution from Figure 2

| data-management aspect | number of studies |
|---|---:|
| Data Analysis | 19 |
| Data Collection | 19 |
| Data Integration | 18 |
| Data Quality | 13 |
| Data Visualization | 9 |
| Data Storage | 8 |
| Data-Driven Decision Making | 7 |
| Data Ingestion | 6 |
| Data Privacy | 6 |
| Data Management Development | 6 |
| Data Validation and Governance | 5 |
| Data-Driven Development | 4 |
| Data Testing | 4 |
| Data Security and Compliance | 2 |
| Data Maintenance Strategy | 2 |

#### Facet D — Solution status vocabulary

- Implemented
- Partially implemented
- Proposed

#### Prioritized challenge mapping from Table 2

| aspect group | challenge | studies | potential impact |
|---|---|---:|---|
| Data Integration | Data Harmonization and Interoperability | 4 | High — essential for cross-team workflows |
| Data Integration | Semantic Heterogeneity | 4 | Medium — critical for accurate decision-making |
| Data Integration | Data Transformation and Extraction | 4 | High — impacts real-time data usability |
| Data Integration | Managing Data Integration | 3 | Medium — addresses cross-functional coordination |
| Data Integration | Diverse and Decentralized Data Sources | 3 | High — influences accessibility and consistency |
| Data Collection | Capturing Diverse Data | 3 | High — impacts completeness of agile decisions |
| Data Collection | Comprehensive Data Collection | 3 | Medium — enables broader data applicability |
| Data Collection | Data Sharing and Collaboration | 2 | Medium — improves team alignment |
| Data Collection | Informative Data Collection | 2 | Medium — supports specific project needs |
| Data Quality | Ensuring Data Accuracy and Consistency | 5 | High — critical for decision reliability |
| Data Quality | Missing Quality Data | 3 | High — affects agile sprint outputs |
| Data Quality | Inadequate Data Quality Management | 3 | Medium — increases risk of errors |
| Data Quality | Data Quality Standardization | 2 | Medium — facilitates uniform data processes |
| Data Analysis | Analyzing Large and Complex Data | 5 | High — influences scalability and insights |
| Data Analysis | Analyzing Semantic Heterogeneity Data | 3 | Medium — ensures semantic alignment |
| Data Analysis | Efficient Data Analysis and Visualization | 3 | High — impacts decision-making speed |
| Data Analysis | Real-Time Data Analytics and Decision Making | 2 | High — supports adaptive project actions |
| Data Analysis | Selection of Appropriate Analytical Techniques | 2 | Medium — improves analysis relevance |

#### Challenge-solution-status mapping from Tables 3–6

The following is extractable as a typed mapping. For production, use rows from Tables 3–6 as the canonical source.

##### Data Integration — Table 3

| challenge | solution | status | ref |
|---|---|---|---|
| Data Harmonization and Interoperability | Development of ontologies | Proposed | [37] |
| Data Harmonization and Interoperability | Cloud-based platform with agile data-loading pipeline | Implemented | [39] |
| Data Harmonization and Interoperability | Agile workflow for integrating data | Proposed | [45] |
| Data Harmonization and Interoperability | Translating datasets' metadata into different formats | Implemented | [42] |
| Semantic Heterogeneity | Communication-centric approach with agile methods | Implemented | [13] |
| Semantic Heterogeneity | Development of ontology-based approach | Proposed | [34] |
| Semantic Heterogeneity | Development of domain ontologies | Implemented | [19] |
| Semantic Heterogeneity | Modular and agile framework | Implemented | [38] |
| Data Transformation and Extraction | Advanced ETL procedures | Implemented | [40] |
| Data Transformation and Extraction | Data visualization and federation layer | Proposed | [44] |
| Data Transformation and Extraction | Replicable ETL process | Implemented | [18] |
| Data Transformation and Extraction | Shift to advanced analytic platforms | Proposed | [43] |
| Managing Data Integration | Data mesh approach | Proposed | [4] |
| Managing Data Integration | Microsoft Solutions Framework | Implemented | [41] |
| Managing Data Integration | Architecture-centric approach with AABA methodology | Implemented | [32] |
| Diverse and Decentralized Data Sources | Common product-line architecture | Implemented | [33] |
| Diverse and Decentralized Data Sources | Automated Continuous Quality metrics dashboard | Partially implemented | [35] |
| Diverse and Decentralized Data Sources | Ref in Section 3.2.5 | Partially implemented | [36] |

##### Data Collection — Table 4

| challenge | solution | status | ref |
|---|---|---|---|
| Capturing Diverse Data | User-centered design strategies | Implemented | [20] |
| Capturing Diverse Data | Continuous Integration tools | Proposed | [8] |
| Capturing Diverse Data | Analytics-Driven Testing | Proposed | [15] |
| Data Collection Methods | Automated Testing Dashboards | Partially implemented | [35] |
| Data Collection Methods | Toolchain automation | Proposed | [52] |
| Data Collection Methods | Human-centred agile platform | Proposed | [57] |
| Data Collection Methods | Automated methods | Proposed | [50] |
| Data Collection Methods | Centralized data management | Proposed | [36] |
| Data Sharing and Collaboration | Diagnostic model | Proposed | [2] |
| Data Sharing and Collaboration | DDSE methodologies | Proposed | [47] |
| Data Sharing and Collaboration | Include a legal advisor for compliance | Proposed | [46] |
| Informative Data Collection | Ontology-based approach | Proposed | [34] |
| Informative Data Collection | Integrating project data into retrospectives | Proposed | [55] |
| Informative Data Collection | Q-Rapids tool | Implemented | [48] |
| Informative Data Collection | Data analyst collaboration | Proposed | [43] |
| Comprehensive Data Collection | Creation of a generalized dataset | Proposed | [54] |
| Comprehensive Data Collection | Big data stack | Proposed | [9] |
| Comprehensive Data Collection | Project Management Information System | Proposed | [58] |
| Comprehensive Data Collection | Automated data collection mechanisms | Proposed | [56] |

##### Data Quality — Table 5

| challenge | solution | status | ref |
|---|---|---|---|
| Ensuring Data Accuracy and Consistency Across Varied Sources | Ref in Section 3.2.4 | Implemented | [13] |
| Ensuring Data Accuracy and Consistency Across Varied Sources | Ref in Section 3.2.4 | Implemented | [33] |
| Ensuring Data Accuracy and Consistency Across Varied Sources | Ref in Section 3.2.4 | Implemented | [41] |
| Ensuring Data Accuracy and Consistency Across Varied Sources | Ref in Section 3.2.5 | Implemented | [20] |
| Ensuring Data Accuracy and Consistency Across Varied Sources | Ref in Section 3.2.4 | Implemented | [18] |
| Missing Quality Data | Quality-aware models | Implemented | [1] |
| Missing Quality Data | Ref in Section 3.2.5 | Proposed | [52] |
| Missing Quality Data | Ref in Section 3.2.5 | Proposed | [48] |
| Inadequate Data Quality Management | Test-driven approaches | Proposed | [51] |
| Inadequate Data Quality Management | Ref in Section 3.2.4 | Implemented | [40] |
| Inadequate Data Quality Management | Ref in Section 3.2.4 | Implemented | [50] |
| Data Quality Standardization | Ref in Section 3.2.5 | Implemented | [39] |
| Data Quality Standardization | Ref in Section 3.2.5 | Proposed | [15] |

##### Data Analysis — Table 6

| challenge | solution | status | ref |
|---|---|---|---|
| Analyzing Large and Complex Data | Ref in Section 3.2.4 | Proposed | [32] |
| Analyzing Large and Complex Data | Ref in Section 3.2.5 | Proposed | [43] |
| Analyzing Large and Complex Data | Ref in Section 3.2.5 | Proposed | [54] |
| Analyzing Large and Complex Data | Ref in Section 3.2.5 | Proposed | [57] |
| Analyzing Large and Complex Data | Well-documented tools and developer training | Proposed | [59] |
| Analyzing Semantic Heterogeneity Data | Ref in Section 3.2.4 | Proposed | [34] |
| Analyzing Semantic Heterogeneity Data | Ref in Section 3.2.4 | Implemented | [19] |
| Analyzing Semantic Heterogeneity Data | Ref in Section 3.2.4 | Implemented | [38] |
| Efficient Data Analysis and Visualization | Ref in Section 3.2.4 | Proposed | [44] |
| Efficient Data Analysis and Visualization | Ref in Section 3.2.5 | Proposed | [50] |
| Efficient Data Analysis and Visualization | Ref in Section 3.2.5 | Proposed | [52] |
| Efficient Data Analysis and Visualization | Ref in Section 3.2.5 | Proposed | [2] |
| Real-Time Data Analytics and Decision Making | Ref in Sections 3.2.4 and 3.2.5 | Proposed | [35] |
| Real-Time Data Analytics and Decision Making | Ref in Section 3.2.5 | Proposed | [56] |
| Selection of Appropriate Analytical Techniques | Ref in Section 3.2.4 | Implemented | [33] |
| Selection of Appropriate Analytical Techniques | Ref in Section 3.2.5 | Proposed | [8] |
| Selection of Appropriate Analytical Techniques | Ref in Section 3.2.5 | Proposed | [55] |
| Selection of Appropriate Analytical Techniques | Ref in Section 3.2.5 | Proposed | [58] |
| Selection of Appropriate Analytical Techniques | Ref in Section 3.2.5 | Proposed | [15] |

#### Multi-label overlap structure from Figure 3

Figure 3 is not a tree. It is a Venn-like overlap among four focus aspects. Preserve as multi-label memberships keyed by study reference IDs if extracted.

Facet values visible in the figure:

- Data Collection: 19 studies
- Data Integration: 18 studies
- Data Analysis: 19 studies
- Data Quality: 13 studies

Recommended data model: `study_ref -> set[data_management_aspect]`. Do not flatten overlaps into hierarchical child nodes.

### 4. Evidence Ledger

| evidence_id | locator | compact transcription / paraphrase | supports |
|---|---|---|---|
| P2-E1 | PDF p. 12, Section 3.2.1 | The paper defines four top aspects and points remaining definitions to replication package. | Aspect semantics and limitation. |
| P2-E2 | PDF p. 13, Figure 2 | Fifteen aspect names with study counts are visible in rendered chart. | Fifteen-aspect inventory and counts. |
| P2-E3 | PDF p. 14, Table 1 | Table caption: classifications of studies across data-management aspects. | Aspect-to-study mapping. |
| P2-E4 | PDF p. 15, Figure 3 | Overlap diagram among four key aspects. | Multi-label relationship among aspects/studies. |
| P2-E5 | PDF p. 17, Table 2 | Grouped challenges with study counts and impact levels. | Challenge classification structure. |
| P2-E6 | PDF p. 17, Table 3 | Challenge-solution-status-ref mapping for Data Integration. | Typed mapping extraction. |
| P2-E7 | PDF p. 23, Table 4 | Challenge-solution-status-ref mapping for Data Collection. | Typed mapping extraction. |
| P2-E8 | PDF p. 27, Table 5 | Challenge-solution-status-ref mapping for Data Quality. | Typed mapping extraction. |
| P2-E9 | PDF p. 30, Table 6 | Challenge-solution-status-ref mapping for Data Analysis. | Typed mapping extraction. |

### 5. Rejected Candidates

| candidate | reason for rejection |
|---|---|
| Figure 1 SLR process | Literature-review workflow, not a domain taxonomy. |
| Quality assessment score bins | Methodological quality categories, not the data-management taxonomy. |
| Survey demographic charts | Descriptive survey metadata, not taxonomy unless they reuse the challenge/aspect categories. |
| Section headings alone | Not sufficient without table/prose support. |
| Raw search strings | Search strategy, not conceptual categories. |

### 6. Open Questions / Blockers

No blocker for audit. Important scope limitation: the PDF defines four top aspects directly, while definitions for the other eleven aspects are said to be in a replication package. Therefore, a PDF-only extraction can confidently extract the names, counts, references, and mappings for all fifteen aspects, but full semantic definitions for all fifteen require the replication package or manual domain annotation.

---

## 084_2501.18845 — Text Data Augmentation for Large Language Models: A Comprehensive Survey of Methods, Challenges, and Opportunities

### 1. Decision

| field | value |
|---|---|
| taxonomy_status | explicit |
| taxonomy_kind | taxonomy_like_dag |
| worth full manual extraction | yes, highest priority |
| confidence | high |

This is the highest-priority extraction target. The paper explicitly classifies text data augmentation for LLMs into four technique categories and includes a detailed rendered method tree in Figure 4. It should be represented as a taxonomy-like DAG rather than a strict tree because hybrid methods are cross-listed under prompt/retrieval branches and under the Hybrid Augmentation branch.

### 2. Evidence Checked

| locator | evidence checked | audit note |
|---|---|---|
| PDF printed p. 1 / parser P0, abstract/introduction | Prose classification into four categories | Explicitly names Simple, Prompt-based, Retrieval-based, and Hybrid Augmentation. |
| PDF printed p. 2 / parser P1, Figure 1 | Rendered example panels | Four technique categories are visible as examples. |
| PDF printed p. 4 / parser P3, Table I | Rendered table body | Methods are grouped by technique category and checked against augmentation aspects. |
| PDF printed p. 6 / parser P5, Table II | Rendered table body | Methods are grouped by technique category and checked against augmentation granularity. |
| PDF printed p. 8–9 / parser P7–P8, Section III and Figure 3 | Prose and rendered two-axis figure | Classifies techniques by Prompt Complexity and Retrieval Model Complexity. |
| PDF printed p. 10 / parser P9, Figure 4 | Rendered detailed tree body and caption | Detailed method taxonomy rooted at “Text Data Augmentation Techniques in LLMs.” |
| PDF printed p. 13 / parser P12, Section IV | Post-processing prose | Defines smaller post-processing categories; secondary extraction target. |

### 3. Extracted Candidate Taxonomy

Recommended representation: taxonomy-like DAG. Preserve grey-font hybrid cross-listing and duplicate/cross-listed method names. Do not deduplicate into a single tree unless the downstream schema supports cross-references.

#### Main root and four top-level categories

- Text Data Augmentation Techniques in LLMs
  - Simple Augmentation
  - Prompt-based Augmentation
  - Retrieval-based Augmentation
  - Hybrid Augmentation

#### Detailed method tree from Figure 4

- Text Data Augmentation Techniques in LLMs
  - Simple Augmentation
    - Text Transformation
      - GenAug [12]
      - DAGAM [11]
      - MRC-QA [19]
    - Seed Selection Strategies
      - Selection-DA [15]
    - Back-translation
      - AuGPT [13]
    - Sequence-based Methods
      - COCA [14]
      - TransformersDA [10]
      - LAMBADA [16]
      - LeCA [17]
      - G-DAUGc [18]
  - Prompt-based Augmentation
    - Single-step Prompts
      - Cloze Prompting
        - FlipDA [4]
        - GENIUS [5]
        - SUNGEN [31]
      - Zero-shot Prompting
        - DA-NMT [26]
        - ZeroShotDataAug [28]
        - UDAPDR [46]
        - DAPDR [45]
        - Generative-DA [33]
        - UniMS-RAG [65]  <!-- grey/hybrid in figure -->
      - Few-shot Prompting
        - AugGPT [2]
        - EPA [27]
        - DAIL [25]
        - Promptagator [44]
        - InPars [42]
        - DA-intent [21]
        - LLM-Assisted [3]
        - Read-Com [24]
        - Dialogue-Convert [29]
        - UDAPDR [46]
        - Synthetic-DA [36]
        - RADA [64]  <!-- grey/hybrid in figure -->
        - DAICL [61]  <!-- grey/hybrid in figure -->
        - QA-Internet [8]  <!-- grey/hybrid in figure -->
        - ALCE [63]  <!-- grey/hybrid in figure -->
    - Multi-step Prompts
      - Chain-of-Thought Prompting
        - LLM-PTM [32]
        - LLM-Assisted [3]
        - ConvAug [43]
        - ReAct [66]  <!-- grey/hybrid in figure -->
    - Structured Prompts
      - Role Prompting
        - AugESC [23]
        - ICLEF [34]
      - Tuple Prompting
        - GPT3Mix [20]
        - KAPING [62]  <!-- grey/hybrid in figure -->
      - Template Prompting
        - HiPSTG [30]
        - LLM2LLM [37]
        - LLM-DA [35]
        - TAPP [40]
        - PromptMix [38]
        - LLM-powered [1]
        - WANLI [22]
        - Unnatural-instructions [39]
        - X-GEAR [41]
  - Retrieval-based Augmentation
    - Sparse Retrieval
      - BM25
        - AugmentedSBERT [47]
        - ALCE [63]  <!-- grey/hybrid in figure -->
        - UniMS-RAG [65]  <!-- grey/hybrid in figure -->
      - TF-IDF
        - CGRG [54]
        - UniMS-RAG [65]  <!-- grey/hybrid in figure -->
    - Dense Retrieval
      - ANCE
        - RetGen [7]
      - Contriever
        - LAPDOG [59]
      - Poly-encoder
        - EDGE [52]
      - S-BERT
        - EAE-RAG [56]
        - RGQA [53]
      - RoBERTa
        - Efficient-RAG [58]
      - SimCSE
        - zicl [48]
        - DAICL [61]  <!-- grey/hybrid in figure -->
      - DPR
        - IM-RAG [55]
        - ALCE [63]  <!-- grey/hybrid in figure -->
      - TAS-B
        - RADA [64]  <!-- grey/hybrid in figure -->
      - GTR
        - ALCE [63]  <!-- grey/hybrid in figure -->
    - Graph-based Retrieval
      - Personae-DA [60]
      - KAPING [62]  <!-- grey/hybrid in figure -->
    - Search Engine Retrieval
      - Wikipedia Search
        - DialogGen [50]
      - APIs
        - ChatPLUG [51]
        - Internet-Aug [49]
        - SeeKeR [57]
        - ReAct [66]  <!-- grey/hybrid in figure -->
        - QA-Internet [8]  <!-- grey/hybrid in figure -->
  - Hybrid Augmentation
    - DAICL [61]
    - KAPING [62]
    - QA-Internet [8]
    - SeeKeR [57]
    - ALCE [63]
    - KAPING [62]  <!-- duplicate visible in figure -->
    - RADA [64]
    - ReAct [66]
    - UniMS-RAG [65]

#### Facet A — Prompt Complexity from Figure 3

- No Prompt
- Basic
- Advanced

#### Facet B — Retrieval Model Complexity from Figure 3

- No Retrieval
- Basic
- Advanced

#### Figure 3 placement summary

| technique category | prompt complexity | retrieval complexity | visible internal categories |
|---|---|---|---|
| Simple Augmentation | No Prompt | No Retrieval | Text Transformation, Seed Selection Strategies, Back-translation, Sequence-based Methods |
| Prompt-based Augmentation | Basic to Advanced | No Retrieval | Single-step Prompts, Multi-step Prompts, Structured Prompts |
| Retrieval-based Augmentation | No Prompt | Basic to Advanced | Sparse Retrieval, Dense Retrieval, Graph-based Retrieval, Search Engine Retrieval |
| Hybrid Augmentation | Basic to Advanced | Basic to Advanced | Prompt branch plus retrieval branch; figure shows interaction between prompt and retrieval components |

#### Facet C — Data augmentation aspects from Table I

- Generation
- Paraphrasing
- Translation
- Labeling
- Retrieval
- Editing

Recommended data model: `method -> set[aspect]` because rows can have multiple checkmarks.

#### Facet D — Data augmentation granularity from Table II

- Token Level
- Token-span Level
- Sentence Level
- Passage Level
- Context Level
- Document Level

Recommended data model: `method -> set[granularity]` because rows can have multiple checkmarks.

#### Facet E — Post-processing approaches from Section IV

Secondary extraction target:

- Consistency Measures
- Filtering Techniques
- Heuristic Methods
- Human Involvement

### 4. Evidence Ledger

| evidence_id | locator | compact transcription / paraphrase | supports |
|---|---|---|---|
| P3-E1 | PDF p. 1, abstract/introduction | Four top-level augmentation categories are explicitly named. | Explicit taxonomy status. |
| P3-E2 | PDF p. 2, Figure 1 | Four example panels correspond to the four categories. | Rendered visual support for top-level categories. |
| P3-E3 | PDF p. 4, Table I | Method rows grouped by four categories and checked across six aspects. | Aspect facet and method-to-aspect mapping. |
| P3-E4 | PDF p. 6, Table II | Method rows grouped by four categories and checked across six granularity levels. | Granularity facet and method-to-granularity mapping. |
| P3-E5 | PDF p. 9, Figure 3 | Two axes: prompt complexity and retrieval complexity. | Faceted two-axis classification. |
| P3-E6 | PDF p. 10, Figure 4 | Rooted detailed method taxonomy; grey text marks hybrid cross-listing. | Main tree/DAG extraction target. |
| P3-E7 | PDF p. 13, Section IV | Post-processing approaches are grouped into four categories. | Secondary category system. |

### 5. Rejected Candidates

| candidate | reason for rejection |
|---|---|
| Whole paper outline | The extraction target is Figure 4, Figure 3, Tables I–II, and explicit prose, not the section hierarchy. |
| LLM architecture background split | Encoder-only / decoder-only / encoder-decoder is background, not the paper’s augmentation taxonomy. |
| Table III tasks/subtasks/datasets | Useful task inventory, but secondary and not the main augmentation method taxonomy. |
| Table IV evaluation metrics | Metrics inventory; not the primary taxonomy unless metric taxonomy is explicitly requested. |
| Figure 2 chronology/timeline | Useful for history but not necessary once Figure 4 and Tables I–II are extracted. |

### 6. Open Questions / Blockers

No blocker for audit. For production extraction, preserve cross-listing. Grey-font methods in Figure 4 are hybrid methods shown under prompt/retrieval sub-branches, and the Hybrid Augmentation branch also lists them. KAPING appears twice in the visible Hybrid branch; keep the duplicate as a source-observed duplication until source TeX or author intent confirms whether it is an error.

---

# Final Recommendation

## Extraction Priority Ranking

1. `084_2501.18845` — highest priority. Richest and most explicit taxonomy: detailed Figure 4 tree/DAG, Figure 3 two-axis classification, Table I aspect facet, and Table II granularity facet.
2. `002_2404.03282` — second priority. Clean explicit five-field faceted notation with a direct publication-to-field mapping in Table 4.
3. `055_2402.00462` — third priority. Extractable and useful, but it is a thematic SLR coding/mapping structure rather than a formal taxonomy.

## Extract Now

- `084_2501.18845`
- `002_2404.03282`
- `055_2402.00462` if the pipeline accepts SLR-derived thematic category systems and challenge-solution mappings as taxonomy-like structures.

## Keep as Ambiguous

- None.

## Reject as `none_found`

- None.

# Codex-Oriented Extraction Guidance

## Recommended JSON-like schema for `002_2404.03282`

```json
{
  "paper_id": "002_2404.03282",
  "taxonomy_status": "explicit",
  "taxonomy_kind": "faceted_taxonomy",
  "root_label": "Patient transport problem classification notation",
  "facets": [
    {"id": "alpha", "label": "Fleet characteristics", "values": []},
    {"id": "beta", "label": "Depot characteristics", "values": []},
    {"id": "gamma", "label": "Constraints", "values": []},
    {"id": "delta", "label": "Problem objectives", "values": []},
    {"id": "epsilon", "label": "Uncertainty", "values": []}
  ],
  "classified_items": [
    {
      "item_type": "publication",
      "source_table": "Table 4",
      "assignments": {"alpha": [], "beta": [], "gamma": [], "delta": [], "epsilon": []}
    }
  ]
}
```

## Recommended JSON-like schema for `055_2402.00462`

```json
{
  "paper_id": "055_2402.00462",
  "taxonomy_status": "taxonomy_like",
  "taxonomy_kind": "faceted_taxonomy",
  "facets": [
    {"id": "data_management_aspect", "values": []},
    {"id": "challenge", "values": []},
    {"id": "potential_impact", "values": ["High", "Medium"]},
    {"id": "solution_status", "values": ["Implemented", "Partially implemented", "Proposed"]}
  ],
  "relations": [
    {"type": "study_has_aspect", "source": "Table 1 / Figure 3"},
    {"type": "aspect_has_challenge", "source": "Table 2"},
    {"type": "challenge_has_solution", "source": "Tables 3-6"},
    {"type": "solution_has_status", "source": "Tables 3-6"}
  ]
}
```

## Recommended JSON-like schema for `084_2501.18845`

```json
{
  "paper_id": "084_2501.18845",
  "taxonomy_status": "explicit",
  "taxonomy_kind": "taxonomy_like_dag",
  "root_label": "Text Data Augmentation Techniques in LLMs",
  "top_level_categories": [
    "Simple Augmentation",
    "Prompt-based Augmentation",
    "Retrieval-based Augmentation",
    "Hybrid Augmentation"
  ],
  "nodes": [],
  "edges": [
    {"type": "parent_child", "source": "Figure 4"},
    {"type": "hybrid_cross_listing", "source": "Figure 4 grey text"},
    {"type": "method_has_aspect", "source": "Table I"},
    {"type": "method_has_granularity", "source": "Table II"}
  ],
  "facets": [
    {"id": "prompt_complexity", "values": ["No Prompt", "Basic", "Advanced"]},
    {"id": "retrieval_model_complexity", "values": ["No Retrieval", "Basic", "Advanced"]},
    {"id": "augmentation_aspect", "values": ["Generation", "Paraphrasing", "Translation", "Labeling", "Retrieval", "Editing"]},
    {"id": "augmentation_granularity", "values": ["Token Level", "Token-span Level", "Sentence Level", "Passage Level", "Context Level", "Document Level"]}
  ]
}
```

# Implementation Notes for Codex

1. Use `taxonomy_status` as the binary gate only after applying the audit rules. `explicit` and `taxonomy_like` are extraction-eligible; `none_found` is not.
2. For `faceted_taxonomy`, produce facets and row mappings. Do not create artificial parent-child depth.
3. For `taxonomy_like_dag`, preserve duplicate or cross-listed method nodes with source locators. Add canonical IDs later if normalization is needed.
4. Use PDF page locators and figure/table numbers in every extracted node or relation. This allows later verification and rollback.
5. Keep `rejected_candidates` in the output metadata. This prevents future agents from re-extracting PRISMA diagrams, section outlines, performance tables, or dataset inventories as false taxonomies.
6. For dense tables with rotated or compact math notation, store a `needs_tex_confirmation: true` flag if exact subscripts matter.
