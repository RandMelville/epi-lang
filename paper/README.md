# Epi — SBLP 2026 Short Paper

LaTeX source for the SBLP 2026 short-paper submission, written against
the **CBSoft 2026 ACM-like template** (`acmart` with `sigconf` option).

```
paper/
├── main.tex                          # Manuscript (LaTeX)
├── refs.bib                          # BibTeX bibliography
├── sblp2026-short-draft.md           # Original Markdown draft (history)
├── review-main-20260527-1415.md      # Architect/Stylist/Reviewer report
└── README.md                         # This file
```

## What was applied in the 2026-05-27 revision

The current `main.tex` incorporates Tier 1 + Tier 2 + Tier 3 fixes from
`review-main-20260527-1415.md`:

- **Abstract reframed** from capability claim to demonstration claim
  (`We evaluate` → `We exercise`).
- **Contribution 4** explicitly qualified as "a worked example, not a
  controlled study".
- **§5 renamed** `Empirical Evaluation` → `Demonstration`. The
  "Empirical scope" paragraph that was buried in §6 now opens §5, so
  reviewers read the scope qualifier before the table.
- **§3 now contains an EBNF fragment** (productions for `entity_decl`,
  `field_decl`, `rigid_type`, `epistemic_type`, `pulse_decl`).
  Resolves the "Contribution 2 asserted-not-shown" weakness — a
  Brazilian PL venue requires at least a glimpse of the grammar.
- **§3 explicitly states the non-interference invariant** the
  transpiler maintains, and §6 now refers to that invariant rather
  than introducing the property only at the end.
- **§3 includes one explicit BAML/DSPy contrast sentence**, naming
  artifact (3) as the only one BAML/DSPy generates.
- **Table now has four rows and a Claude column.** The malformed-JSON
  containment event is no longer buried in prose; it is the fourth
  row. The Claude column makes provider parity visible, not asserted.
- **§5 Observation now closes the loop on BAML/DSPy** explicitly
  ("BAML and DSPy would type-validate the value; only Epi additionally
  emits the Checkpoint dispatch and the audit trail").
- **§7 Conclusion rewritten** per the Stylist proposal: dropped
  "Future work includes...", replaced with "Three directions follow:".
- **All Stylist Before/After edits applied** through abstract, §1, §2,
  §3, §5, §6, §7, and Artifact Availability.
- **Grammar fix at "Submitting...returned"** (dangling subject).
- **`listings` package removed entirely**, replaced by `verbatim`.
  The earlier compile attempt failed with
  `LaTeX Error: Missing \begin{document}` due to a conflict between
  `listings` (with escaped `\_` in `morekeywords`) and `acmart`.
  `verbatim` produces less-pretty code blocks but compiles cleanly on
  any Overleaf project derived from the CBSoft template.

## Compiling on Overleaf

1. Open the official SBLP 2026 template on Overleaf:
   <https://www.overleaf.com/read/cyhpwwkngcwk>
2. **Menu → Copy Project** (creates your editable copy).
3. In your copy:
   - Delete the sample `main.tex` and upload `paper/main.tex` from this folder.
   - Delete the sample bibliography file and upload `paper/refs.bib`.
4. Confirm the compiler is set to **pdfLaTeX** with **BibTeX**.
5. Click **Recompile**.

The current camera-ready compiles to 6 pages, of which 4.93 are body and
the rest references. See the page budget section below before adding
anything.

## Switching between visible and anonymous versions

`acmart` handles double-blind anonymization through a documentclass
option. You do **not** need to comment out `\author` blocks manually.

- **Visible (current, for co-author review):**
  ```latex
  \documentclass[sigconf]{acmart}
  ```
- **Anonymous (for JEMS3 double-blind submission):**
  ```latex
  \documentclass[sigconf,anonymous,review]{acmart}
  ```

With `anonymous`, author blocks render as "Anonymous Author(s)". With
`review`, line numbers appear for reviewers.

Switch the option, recompile, and submit. No other edits required.

## Compiling locally (alternative)

```bash
pdflatex main.tex
bibtex   main
pdflatex main.tex
pdflatex main.tex
```

You need TeX Live ≥ 2019 (which includes `acmart`).

## Page budget

**The limit comes from the CfP, never from the previous version.** SBLP
2026 short papers get **4 pages excluding references**, plus **one extra
page for the camera-ready** to absorb reviewer changes, which the chairs
confirmed by email. That is a ceiling of **5 body pages**; the reference
pages do not count.

This was got wrong once. An earlier round read "the submitted version is
6 pages, the camera-ready may use one more" as a 7-page budget and never
opened the CfP, so the camera-ready was closed on 2026-07-29 at 6.6 body
pages, 1.6 over. It was cut back to 4.93 on 2026-07-30.

Measure the body, not the PDF: compile, find where the `REFERENCES`
heading starts, and count everything before it. `pdftotext -bbox` gives
the position.

## Camera-ready (accepted, weak accept from 4 reviewers)

Deadline: **1 August 2026**. Submit via JEMS3:
<https://jems3.sbc.org.br/events/462>.

Applied in this round, mapped to the reviewer that asked for it:

- **§5.1 + Table 2**, containment over 40 curated inputs against Qwen
  2.5 3B and Llama 3.2 1B, with the harness in `eval/`. Answers the
  "single running example is insufficient" objection raised by
  reviewers 1, 3 and 4.
- **Grammar now covers all five declaration forms** (Entity, Guard,
  Pulse with `pulse_body`, Trace, Pipeline, Lens). Reviewer 3 noted
  that only Entity and part of Pulse were specified.
- **Epistemic types other than `AI.Enum`** given a paragraph stating
  how far containment reaches for each. Reviewer 4.
- **§4 rewritten to justify the design**, in particular why the
  generator split is by epistemic domain and not by output artifact.
  Reviewers 3 and 4.
- **`_confidence` documented as prompt-elicited**, not derived from
  logprobs, with the 0.5 default that fails towards review.
- **Composition order between `prior` and `confidence_threshold`**
  stated: they do not compose today, and the posterior comparison is
  named as future work in §6.
- **Trace audit record described accurately**: the emitted store is an
  in-process map behind a save/get/update interface, not a durable
  backend. The previous wording claimed a persistent audit trail.
- **BAML/DSPy comparison reduced** from five mentions to four, each
  doing distinct work. Reviewer 4 flagged the repetition; reviewer 2
  asked for the comparison in the abstract and the conclusion, so it
  cannot go below that.
- **Portuguese identifier removed** from §5.1 (`Input.resposta_aluno`).
  Reviewers 2 and 4.
- **Verbatim blocks reflowed to 42 columns**, which fixes the overfull
  lines reviewer 2 pointed at (`Checkpoint.ReviewRequired`,
  `Fallback.ManualReview`, `On_Error: Retry`) and the EBNF, which had
  the same problem.
- **Acknowledgements uncommented**, now also thanking the reviewers.

Before uploading:

- [ ] Recompile on Overleaf and check the page count. Prose grew by
      about 660 words and 14 verbatim lines against the version that
      compiled to 7 pages, so expect roughly three quarters of a page
      more. Cut list below if it spills.
- [ ] If the CfP requires a declaration on the use of generative AI
      tools, add it to the Acknowledgements section.
- [ ] Verify no overfull box warnings remain in the log.

Cut list, in priority order, if the page count has to come down:

1. The paragraph in §3 on epistemic types other than `AI.Enum`
   (~110 words). Costs reviewer 4's request.
2. The second paragraph of §4, on why the split is by domain
   (~140 words). Costs the design justification reviewers 3 and 4
   asked for.
3. The last paragraph of §5.1, on the three limitations. Honest but
   the structural result survives without it.
4. The `Guard` and `Pipeline` blocks of the §5 listing, replaced by
   one sentence. Breaks the "reproduced in full" claim.
5. The SlicStan or the Wasp sentence in §2.
