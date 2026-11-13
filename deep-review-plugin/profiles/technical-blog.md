# Review profile: technical blog post or tutorial

The reader is a practitioner who will copy the code and repeat the claims. The document succeeds if what it states is correct, its measurements support its conclusions, and a reader can reproduce it.

Treat as errors:
- Technical statements that are wrong or imprecise: how a hardware feature, library call, algorithm or data format works; what an API argument does; attributions of a result to the wrong cause.
- Numbers that do not reconcile: arithmetic in tables and text, ratios, percentages, totals, values that differ between the summary, body, code and figures.
- Code that does not match the prose, would not run as shown, or differs between two listings of the same thing.
- Hardware, software, model and dataset facts: product specifications, version behaviour, parameter counts, figures quoted from papers, datasheets or other people's work.
- Causal explanations offered as established when the post's own measurements do not isolate them (an ordering effect, a confound, a single run).

Treat as gaps:
- Missing setup needed to reproduce or interpret a measurement: batch size, sequence length, number of runs, warm-up, variance, software versions.
- Claims in the title, summary or conclusion that the body does not deliver, and body results missing from the conclusion.
- Missing check that quality is preserved when speed is claimed.

Treat as clarity issues: undefined terms, terms used with two meanings, inconsistent naming, typos, formatting.
