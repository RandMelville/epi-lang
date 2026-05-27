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

You should obtain a 4-page PDF.

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

- Limit: **4 pages excluding references** (SBLP short paper).
- Current body is approximately 2,640 words plus one table and two
  short verbatim blocks (EBNF fragment, one `.epi` snippet). This
  should fit four pages in `sigconf` two-column layout.
- If the compiled PDF overflows, apply cuts in priority order:
  1. Drop the SlicStan or DSPy paragraph in §2.
  2. Compress P1/P2/P3 in §1 into one paragraph.
  3. Shorten the EBNF fragment to four productions (`entity_decl`,
     `field_decl`, `rigid_type`, `epistemic_type`).
  4. Drop the "Hallucination containment" subsection at the end of §5
     (the message is implicit in the table's fourth row).

## Pre-submission checklist

- [ ] Switch to `\documentclass[sigconf,anonymous,review]{acmart}`.
- [ ] Recompile; verify the byline shows "Anonymous Author(s)".
- [ ] Re-check that the body has no first-person phrasing that
      identifies the team.
- [ ] Re-check that no figure, table, or footnote leaks identifying
      information (the Artifact Availability section already has a
      bracketed placeholder for the URL).
- [ ] Recompile once more; verify reviewer line numbers appear.
- [ ] Save the PDF and submit via JEMS3:
      <https://jems3.sbc.org.br/events/462>.
- [ ] Deadline: **1 June 2026** (firm, no extensions).

## After acceptance

When the paper is accepted and you switch back to the camera-ready
version:

- [ ] Remove `anonymous,review` from the documentclass.
- [ ] Recompile and verify author names appear.
- [ ] Uncomment the `\section*{Acknowledgements}` block in `main.tex`.
- [ ] In `\section*{Artifact Availability}`, replace the bracketed
      placeholder with the real repository URL and landing-page URL.
- [ ] Recompile; submit the camera-ready PDF.

## Open questions deferred to camera-ready (Tier 4 from the review)

- Stability of Qwen's `_confidence` value across multiple runs of the
  same input. Worth running 5–10 samples and reporting variance in a
  footnote.
- Whether `_confidence` is prompt-elicited or computed from token
  logprobs. State this explicitly in §5.
- For `AI.Enum` with both `prior` and `confidence_threshold`: is the
  threshold compared against raw model confidence or against the
  Bayesian posterior? §3 should specify the composition order.
