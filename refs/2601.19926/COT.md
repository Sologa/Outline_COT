### Step 1: Clustering References into Thematic Categories

- **1 Introduction**: this cluster gathers the papers used to support this standalone theme. Representative references include `rogers_primer_2020` ("A Primer in BERTology: What We Know About How BERT ..."), `zhou_linguistic_2025` ("Linguistic Minimal Pairs Elicit Linguistic Similarity in Large Language Models"), `brinkmann_large_2025` ("Large Language Models Share Representations of Latent Grammatical Concepts Across ..."), `kryvosheieva_controlled_2025` ("Controlled Evaluation of Syntactic Knowledge in Multilingual Language Models").
- **2 Method**: this cluster gathers the papers used to support this standalone theme. Representative references include `lopezotal:etal:2025` ("Linguistic Interpretability of Transformer-based Language Models: a systematic review"), `Milliere:2024` ("Language Models as Models of Language").
- **3 Results**: this cluster groups the references that support this section and its subthemes, especially 3.1 RQ1: Linguistic Phenomena, 3.2 RQ2: Methods, 3.3 RQ3: Knowledge status - BLiMP. Representative references include `Devlin:etal:2019` ("BERT: Pre-training of deep bidirectional transformers for language understanding"), `waldis_holmes_2024` ("Holmes ensuremath recorder A Benchmark to Assess the Linguistic Competence ..."), `lopezotal:etal:2025` ("Linguistic Interpretability of Transformer-based Language Models: a systematic review"), `Milliere:2024` ("Language Models as Models of Language").
- **4 Discussion \& Conclusion**: this cluster gathers the papers used to support this standalone theme. Representative references include `waldis_holmes_2024` ("Holmes ensuremath recorder A Benchmark to Assess the Linguistic Competence ..."), `agarwal:etal:2025` ("Mechanisms vs. Outcomes: Probing for Syntax Fails to Explain Performance ..."), `boleda:2025` ("LLMs as a synthesis between symbolic and continuous approaches to ..."), `lasri_does_2022` ("Does BERT really agree ? Fine-grained Analysis of Lexical Dependence ...").

### Step 2: Generating the Outline from Themes

The final outline follows an IMRaD-like review flow adapted to the domain. It starts with **1 Introduction** to frame the scope and vocabulary of *The Grammar of Transformers: A Systematic Review of Interpretability Research on Syntactic Knowledge in Language Models*, and then expands the review through the major evidence clusters already reflected in the cited references.

- **1 Introduction** remains a top-level unit because the cited material in this span supports one coherent theme without requiring another subdivision layer.
- **2 Method** remains a top-level unit because the cited material in this span supports one coherent theme without requiring another subdivision layer.
- **3 Results** becomes a major theme because its references split naturally into more specific subthemes. Those subthemes are unfolded as **3.1 RQ1: Linguistic Phenomena**; **3.2 RQ2: Methods**; **3.3 RQ3: Knowledge status - BLiMP**, which keeps the hierarchy aligned with the actual citation distribution in the stored outline.
- **4 Discussion \& Conclusion** remains a top-level unit because the cited material in this span supports one coherent theme without requiring another subdivision layer.

The ordering is therefore: 1 Introduction -> 2 Method -> 3 Results -> 4 Discussion \& Conclusion. This keeps broad framing first, develops the domain-specific themes in the middle, and closes only after the main evidence clusters have been covered.

Key Logic:
- The clusters are anchored to the real section numbering and titles, not to an invented template.
- References are mentioned with bib keys that already appear in `outline.json`, so the reasoning stays tied to the stored supervision signal.
- Empty sections are treated as framing or transition nodes rather than back-filled with fabricated citations.
