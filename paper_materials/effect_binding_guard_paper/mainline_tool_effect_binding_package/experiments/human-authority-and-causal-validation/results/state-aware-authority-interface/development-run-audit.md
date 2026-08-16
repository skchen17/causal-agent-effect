# State-Aware Baseline Development Run Audit

The first frozen overlay run completed all 1,024 contexts and produced the
same scientific metrics as the subsequent run, but its status was `failed`.
The integrity check compared the old collision rows to extended rows that also
contained new size, separating-pair, and overpartition fields.  The comparison
was corrected to project the extended rows onto the five immutable legacy
fields before equality testing.

The effect-free view, request adapter, input contexts, authority state, source
oracle, descriptor, and metric calculations were not changed.  The complete
first run and protocol are retained under `archive-v1-check-bug/`.
