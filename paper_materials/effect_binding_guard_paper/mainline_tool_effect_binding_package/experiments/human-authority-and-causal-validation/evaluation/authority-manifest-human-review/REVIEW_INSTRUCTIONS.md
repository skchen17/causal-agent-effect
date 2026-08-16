# E84 Independent Authority Review

The review turns a pre-output LLM proposal into a trusted, task-scoped authority
manifest. Lexical grounding is diagnostic evidence only and does not approve a
binding.

## Inputs

- Immutable template: `review_packet.template.jsonl`
- Reviewer output: `review_packet.reviewed.jsonl`

Copy the template to the reviewer-output filename and edit only the nested
`review` and `human_review` objects. Do not inspect attack goals, injection task
identifiers, benchmark outcomes, or evaluator labels.

## Local Review Interface

The local-only web interface presents the same packet as a guided form and
writes only the reviewer-editable objects to `review_packet.reviewed.jsonl`:

```bash
python scripts/run_e84_authority_review_web.py
```

Open `http://127.0.0.1:8784/` if the browser does not open automatically. The
interface provides task search and filtering, mode-specific fields for
`exact`/`resolve`/`forbidden` bindings, draft saving, progress tracking, and the
same full-packet validation used below. It binds to localhost by default and
does not send review data to an external service.

## Binding Review

For every candidate binding:

1. Set `review.decision` to `APPROVE` or `REJECT` and provide a rationale.
2. For `exact`, record an original-task source span or a declared canonical
   transform.
3. For `resolve`, choose an eligible read tool from `resolver_catalog.json`,
   constrain only declared schema arguments with `exact`/`forbidden` bindings,
   keep `allow_additional_arguments=false`, choose a fixed projection kind, and
   set a maximum cardinality from 1 to 100.
4. For `forbidden`, confirm that the field cannot be expanded by runtime
   evidence.

At task level, provide an anonymous reviewer ID, ISO review date, confirm that
only the original task was used, and set `accepted=true` only when every binding
is approved. Tasks without an acceptable proposal remain rejected and must not
be compiled.

## Validation

```bash
python scripts/validate_e84_authority_review.py
```

The validator checks all 97 task keys, immutable candidate hashes, original-task
hashes, review completeness, exact-value evidence, and bounded resolver
interfaces. It writes `validation_report.json` and creates
`trusted_manifests.jsonl` only when every row passes. A passing packet supports
only the reviewed AgentDojo task set; it is not a production-safety certificate.
