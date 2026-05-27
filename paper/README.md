# Epi — SBLP 2026 Short Paper

LaTeX source for the SBLP 2026 short-paper submission, written against
the **CBSoft 2026 ACM-like template** (`acmart` with `sigconf` option).

```
paper/
├── main.tex                       # Manuscript (LaTeX)
├── refs.bib                       # BibTeX bibliography
├── sblp2026-short-draft.md        # Original Markdown draft (reference)
└── README.md                      # This file
```

## Compiling on Overleaf

The CBSoft template ships the `acmart` class and the `ACM-Reference-Format.bst` style. You should **never** edit those files — only `main.tex` and `refs.bib`.

**Setup:**

1. Open the official SBLP 2026 template on Overleaf:
   <https://www.overleaf.com/read/cyhpwwkngcwk>
2. **Menu → Copy Project** (creates your editable copy).
3. In your copy:
   - Delete the sample `main.tex` and upload `paper/main.tex` from this folder.
   - Delete the sample bibliography file (`sample-base.bib` or similar) and upload `paper/refs.bib`.
4. Confirm the compiler is set to **pdfLaTeX** with **BibTeX**.
5. Click **Recompile**.

You should obtain a 4-page PDF formatted exactly as the CBSoft template specifies.

## Switching between visible and anonymous versions

The `acmart` class handles double-blind anonymization through a documentclass option. You do **not** need to comment out the `\author` blocks manually.

- **Visible (current, for co-author review):**
  ```latex
  \documentclass[sigconf]{acmart}
  ```
- **Anonymous (for JEMS3 double-blind submission):**
  ```latex
  \documentclass[sigconf,anonymous,review]{acmart}
  ```

With `anonymous`, all author blocks render as “Anonymous Author(s)”. With `review`, line numbers are added for reviewers.

Switch the option, recompile, and submit. No other edits required.

## Compiling locally (alternative)

If you prefer compiling on your machine, you need the `acmart` class
(usually present in TeX Live ≥ 2019) and the `ACM-Reference-Format.bst`
style file:

```bash
pdflatex main.tex
bibtex   main
pdflatex main.tex
pdflatex main.tex
```

## Required pieces already in the manuscript

The CBSoft template imposes several requirements; the current `main.tex` already satisfies them:

| Requirement | Status |
|---|---|
| `\documentclass[sigconf]{acmart}` | ✅ |
| `\settopmatter{printacmref=false}` | ✅ |
| `\renewcommand\footnotetextcopyrightpermission[1]{}` | ✅ |
| `\setcopyright{none}` | ✅ |
| `\acmConference[SBLP 2026]{30th Brazilian Symposium on Programming Languages}{...}{São Paulo, SP, Brazil}` | ✅ |
| One `\author{}` + `\affiliation{}` + `\email{}` block per author | ✅ (two authors) |
| `\renewcommand{\shortauthors}{...}` defined | ✅ |
| `\renewcommand{\shorttitle}{...}` defined | ✅ |
| `\frenchspacing` before `\maketitle` | ✅ |
| Abstract as a single continuous paragraph | ✅ |
| `\keywords{}` declared | ✅ |
| Title Case in numbered section titles | ✅ |
| Tables use `\toprule / \midrule / \bottomrule` (no `\hline`, no vertical lines) | ✅ |
| `\section*{Artifact Availability}` after Conclusion, before References | ✅ |
| `\bibliographystyle{ACM-Reference-Format}` and `\bibliography{refs}` | ✅ |

## Page budget

- Limit: **4 pages excluding references** (SBLP short paper).
- If the compiled PDF overflows, apply cuts in priority order:
  1. Drop the SlicStan or DSPy paragraph from Section 2.
  2. Compress P1/P2/P3 in Section 1 into one paragraph.
  3. Remove the "Hallucination containment" sub-paragraph at the end of Section 5 (the malformed-JSON example).
  4. Trim the Conclusion to two sentences.

## Bibliography hygiene

`refs.bib` uses the field set that `ACM-Reference-Format` expects: full author names (no initials), full venue title, series, year, pages, publisher, address, and DOI/URL where applicable. Do **not** abbreviate first names.

The current bibliography contains 9 entries — all third-party, none self-citations — so anonymization is already safe in the bib file.

## Final pre-submission checklist (from the CBSoft template)

- [ ] Switch to `\documentclass[sigconf,anonymous,review]{acmart}`.
- [ ] Recompile; verify the byline shows "Anonymous Author(s)".
- [ ] Re-check that the body has no first-person phrasing that identifies the team.
- [ ] Re-check that no figure, table, or footnote leaks identifying information.
- [ ] Recompile once more; verify reviewer line numbers appear.
- [ ] Save the PDF and submit via JEMS3: <https://jems3.sbc.org.br/events/462>.
- [ ] Deadline: **1 June 2026** (firm, no extensions).

## After acceptance

When the paper is accepted and you switch back to the camera-ready version:

- [ ] Remove `anonymous,review` from the documentclass.
- [ ] Recompile and verify author names appear.
- [ ] Uncomment the `\section*{Acknowledgements}` block in `main.tex` and add the actual text.
- [ ] In `\section*{Artifact Availability}`, replace the bracketed placeholder with the real repository URL and landing-page URL.
- [ ] Recompile; submit the camera-ready PDF.

## Notes for co-authors

The thesis statement is at the end of Section 1: *"LLM hallucination cannot be prevented, but it can be contained at a type-system boundary, by construction, in generated code."* Everything in the paper services this claim. Please challenge it before signing off.

The empirical numbers in Section 5 were measured against the locally generated project; they are reproducible from the open-source repository (URL added at camera-ready).

Title alternatives, if the current one is too long for page headers:

- "Epi: A Type System for AI-Augmented Application Code"
- "Containing LLM Hallucination at a Type-System Boundary"
- "Type-Driven Generation of AI-Augmented Applications"
