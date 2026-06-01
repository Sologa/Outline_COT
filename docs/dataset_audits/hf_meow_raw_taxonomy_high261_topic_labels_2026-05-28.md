# HF MEOW Raw Taxonomy High261 Topic Labels 2026-05-28

This note records the coarse topic labels used for a quick inventory of the
current 261-paper High261 survey/review corpus. It is a dataset-audit note, not
an experiment result and not a manual per-paper gold label set.

## Source

- Input file:
  `data/paper_sets/hf_meow_raw_taxonomy_high261/metadata/hf_meow_raw_high261.with_verified_metadata.plus_openalex_pdf_abstracts.tree50_abstract_recovery_openalex_pdf_merge_20260525_2315_taipei.jsonl`
- Row count checked: `261`
- Classification basis: target paper `raw.meta.title`, `raw.meta.abstract`, and
  `raw.meta.categories`.
- Count basis below: first arXiv category mapped to one coarse label, so counts
  sum to `261`.
- Cross-domain caveat: many papers have multiple arXiv categories. Keep a
  secondary/multilabel field for any later per-paper labeling work.

## Primary Coarse Label Counts

| Label | Count | Notes |
|---|---:|---|
| `ml_ai_methods` | 84 | General ML/AI methods, learning paradigms, graph/federated/few-shot/self-supervised/time-series/modeling surveys. |
| `computer_vision_graphics` | 42 | Computer vision, graphics, visual recognition, 3D, multimodal perception, remote sensing, image/video methods. |
| `ir_data_recommendation` | 37 | Information retrieval, recommender systems, data/DB, semantic search, entity matching, knowledge graph summaries, data quality. |
| `nlp_text_llm` | 29 | NLP, text mining, language models, LLM agents, summarization, NLU, translation, text classification. |
| `security_privacy` | 20 | Security, privacy, safety, attacks/defenses, vulnerability, IDS, model stealing, poisoning, watermarking. |
| `systems_networks_cloud_iot` | 19 | Cloud, fog/edge, networking, NFV, IoT, traffic monitoring, persistent memory, distributed systems. |
| `hci_applied_visualization` | 9 | HCI, visualization, human-AI collaboration, VR education, misinformation interventions, applied human-facing systems. |
| `bio_science_astronomy` | 8 | Primarily astronomy observational-survey rows plus one q-bio row. Some are not literature reviews. |
| `robotics_autonomous_systems` | 7 | Robotics, social navigation, embodied AI, autonomous driving, driving scenario generation. |
| `computers_society` | 6 | Computers and society, public-sector/socio-technical risk, transportation/crowd applications. |

These primary counts sum to `261`.

## Secondary Markers

| Marker | Count | Notes |
|---|---:|---|
| `speech_audio_secondary` | 5 | Secondary-tag only, not a primary label in this 261-row corpus. Based on any `eess.SP`, `eess.SY`, `cs.SD`, or `eess.AS` tag. |

## Label Definitions And Examples

### `ml_ai_methods`

Use for broad AI/ML technique surveys where the main object is the method class,
not a single application domain.

Examples:

- `A Comprehensive Survey on Deep Clustering: Taxonomy, Challenges, and Future Directions`
- `Graph Self-Supervised Learning: A Survey`
- `A Survey on Vertical Federated Learning: From a Layered Perspective`
- `Universal Time-Series Representation Learning: A Survey`
- `A Survey on Dataset Distillation: Approaches, Applications and Future Directions`
- `From Task-Specific Models to Unified Systems: A Review of Model Merging Approaches`

### `computer_vision_graphics`

Use for visual perception, image/video/3D, graphics, and multimodal perception
surveys.

Examples:

- `Deep transfer learning for image classification: a survey`
- `Transformers in 3D Point Clouds: A Survey`
- `A Comprehensive Survey on Data-Efficient GANs in Image Generation`
- `Remote Sensing Object Detection Meets Deep Learning: A Meta-review of Challenges and Advances`
- `A Comprehensive Survey on 3D Content Generation`
- `Editing Implicit and Explicit Representations of Radiance Fields: A Survey`

### `ir_data_recommendation`

Use for recommender systems, information retrieval, semantic search, data
quality, databases, entity matching, and knowledge organization when those are
the main topic.

Examples:

- `A Comprehensive Survey on Multimodal Recommender Systems: Taxonomy, Evaluation, and Future Directions`
- `A Comprehensive Survey on Cross-Domain Recommendation: Taxonomy, Progress, and Prospects`
- `Neural Networks for Entity Matching: A Survey`
- `How to Define the Quality of Data? A Feature-Based Literature Survey`
- `A Survey on Extractive Knowledge Graph Summarization: Applications, Approaches, Evaluation, and Future Directions`
- `Domain Adaptation of Multilingual Semantic Search -- Literature Review`

### `nlp_text_llm`

Use for NLP, text, language models, LLM agents, NLU, summarization, translation,
text classification, and LLM evaluation/safety when the language aspect is the
main topic.

Examples:

- `A survey of joint intent detection and slot-filling models in natural language understanding`
- `Knowledge-aware Document Summarization: A Survey of Knowledge, Embedding Methods and Architectures`
- `Semantic Role Labeling: A Systematical Survey`
- `An In-depth Survey of Large Language Model-based Artificial Intelligence Agents`
- `A Survey on LLM Inference-Time Self-Improvement`
- `Continual Learning for Large Language Models: A Survey`

### `security_privacy`

Use for security, privacy, safety, attacks, defenses, vulnerability, cyber-range,
model-stealing, poisoning, watermarking, and intrusion-detection surveys.

Examples:

- `A Review of Cyber-Ranges and Test-Beds: Current and Future Trends`
- `MITRE ATT&CK: State of the Art and Way Forward`
- `Privacy and Security Implications of Cloud-Based AI Services : A Survey`
- `A Survey on Vulnerability Prioritization: Taxonomy, Metrics, and Research Challenges`
- `I Know What You Trained Last Summer: A Survey on Stealing Machine Learning Models and Defences`
- `Poisoning Attacks and Defenses in Federated Learning: A Survey`

### `systems_networks_cloud_iot`

Use for cloud, fog/edge, networking, IoT, traffic monitoring, distributed
systems, storage/memory systems, and infrastructure operations.

Examples:

- `Reinforcement Learning-based Application Autoscaling in the Cloud: A Survey`
- `NFV Platform Design: A Survey`
- `Application Management in Fog Computing Environments: A Taxonomy, Review and Future Directions`
- `Traffic Behavior in Cloud Data Centers: A Survey`
- `A Survey on UAV-enabled Edge Computing: Resource Management Perspective`
- `Survey of Persistent Memory Correctness Conditions`

### `hci_applied_visualization`

Use for human-facing systems, HCI, visualization, human-AI interaction,
education/VR, trust, misinformation, and applied visual analytics.

Examples:

- `Virtual Reality in Manufacturing Education: A Scoping Review Indicating State-of-the-Art, Benefits, and Challenges Across Domains, Levels, and Entities`
- `The Landscape of User-centered Misinformation Interventions -- A Systematic Literature Review`
- `A Survey of Visual Analytics Techniques for Machine Learning`
- `AI4VIS: Survey on Artificial Intelligence Approaches for Data Visualization`
- `Human-AI collaboration is not very collaborative yet: A taxonomy of interaction patterns in AI-assisted decision making from a systematic review`
- `Tell Me Something That Will Help Me Trust You: A Survey of Trust Calibration in Human-Agent Interaction`

### `bio_science_astronomy`

Use for science-domain topics when they are not better represented by a
method-domain label. In the primary-count table above, this bucket is mainly
astronomy observational-survey papers plus one q-bio tutorial. Biomedical AI
papers often carry CS primary categories in this corpus, so track biomedical
status as a secondary semantic marker if future work needs per-paper labels.

Examples:

- `TransientViT: A novel CNN - Vision Transformer hybrid real/bogus transient classifier for the Kilodegree Automatic Transient Survey`
- `Minimal Morphoelastic Models of Solid Tumour Spheroids: A Tutorial`
- `The Gaia-ESO Survey: Old super-metal-rich visitors from the inner Galaxy`
- `Solaris photometric survey: Search for circumbinary companions using eclipse timing variations`
- `Photometric Properties of Jupiter Trojans detected by the Dark Energy Survey`
- `The eROSITA Final Equatorial-Depth Survey (eFEDS): The AGN Catalogue and its X-ray Spectral Properties`

### `robotics_autonomous_systems`

Use for robotics, social navigation, robot skills, behavior trees, embodied AI,
autonomous driving, and scenario-based autonomous-system testing.

Examples:

- `Conflict Avoidance in Social Navigation -- a Survey`
- `Capability-based Frameworks for Industrial Robot Skills: a Survey`
- `A Survey of Behavior Trees in Robotics and AI`
- `A Survey on Safety-Critical Driving Scenario Generation -- A Methodological Perspective`
- `A Comprehensive Review on Ontologies for Scenario-based Testing in the Context of Autonomous Driving`
- `End-to-end Autonomous Driving using Deep Learning: A Systematic Review`

### `computers_society`

Use for socio-technical, public-sector, risk, crowd, transport, and broader
computers-and-society topics that are not primarily HCI, systems, or security.

Examples:

- `Intelligent Traffic Monitoring Systems for Vehicle Classification: A Survey`
- `A Review on Flight Delay Prediction`
- `Risk assessment at AGI companies: A review of popular risk assessment techniques from other safety-critical industries`
- `Sensing Technologies for Crowd Management, Adaptation, and Information Dissemination in Public Transportation Systems: A Review`
- `Socio-economic landscape of digital transformation & public NLP systems: A critical review`
- `A Survey on Safe Multi-Modal Learning System`

### `speech_audio_secondary`

Use only as a secondary marker in this corpus. No row had speech/audio as the
first coarse label in the inspected 261 rows, but five rows had secondary tags
such as `eess.SP`, `eess.SY`, `cs.SD`, or `eess.AS`.

## Boundary Notes

- Keep single-label counts separate from semantic/multilabel topic tags.
- Do not treat this file as a verified per-paper manual annotation.
- If future work needs per-paper labels, generate a separate JSONL or CSV with
  `paper_id`, `test_index`, `title`, `primary_topic_label`,
  `secondary_topic_labels`, and `label_basis`.
- Astronomy rows containing `Survey` in a proper noun or observational program
  should be reviewed before using the corpus as pure literature-review data.
