# Epi — SBLP 2026 Short Paper

Source files for the SBLP 2026 short-paper submission.

```
paper/
├── main.tex                       # LaTeX source (this is the manuscript)
├── refs.bib                       # BibTeX references
├── sblp2026-short-draft.md        # Original Markdown draft (read-only reference)
└── README.md                      # This file
```

## Compiling on Overleaf

The SBC template (`sbc-template.sty` + `sbc.bst`) is **not** included in this folder.
The official SBLP 2026 Overleaf project already provides it.

**Setup steps:**

1. Open the official template on Overleaf:
   <https://www.overleaf.com/read/cyhpwwkngcwk>
2. Click **Menu → Copy Project** to make your own editable copy.
3. In your copy, delete the example `main.tex` and the example `refs.bib`.
4. Upload `paper/main.tex` and `paper/refs.bib` from this folder.
5. Make sure the compiler is set to **pdfLaTeX** with **BibTeX**.
6. Click **Recompile**.

You should see a 4-page PDF.

## Compiling locally (alternative)

If you prefer compiling on your machine, you need the SBC template files
(`sbc-template.sty` and `sbc.bst`) in the same directory:

```bash
# Download the official template files (one-time)
wget https://www.sbc.org.br/documentos-da-sbc/category/169-templates-para-artigos-e-capitulos-de-livros
# (extract sbc-template.sty and sbc.bst into this paper/ folder)

# Compile
pdflatex main.tex
bibtex   main
pdflatex main.tex
pdflatex main.tex
```

## Before submission to JEMS3 (double-blind)

The current `main.tex` is **not anonymized**: it contains real author names
and affiliation for internal review by co-authors.

**Anonymization checklist before submitting:**

1. In `main.tex`, comment out the visible `\author{}` and `\address{}` blocks.
2. Uncomment the anonymous version provided right below them.
3. Verify the body has no first-person phrasing that identifies the team
   ("at UFRGS we ...", "the first author developed ...").
4. Verify `refs.bib` has no entry citing your own preprints or repository
   under a name that reveals authorship. Currently the bib only cites
   third-party works, so it is already safe.
5. Recompile and confirm the PDF shows `Anonymous Author(s)` in the byline.
6. Submit via JEMS3: <https://jems3.sbc.org.br/events/462>.

## Page budget

- Limit: **4 pages excluding references** (SBLP short paper).
- Current draft, when compiled, should produce approximately 4 pages.
- If it overflows, the recommended cuts (in priority order) are:
  - Drop the SlicStan or DSPy paragraph from Section 2.
  - Compress the three "P1/P2/P3" paragraphs in Section 1 into one paragraph.
  - Remove the "Hallucination containment" subsection at the end of Section 5
    (the message is already implicit in the first table row).

## Notes for co-authors

Before submitting, please review:

- The title (see alternatives in `sblp2026-short-draft.md`).
- The authorship list and order.
- The thesis statement at the end of Section 1 ("LLM hallucination cannot
  be prevented, but it can be contained at a type-system boundary, by
  construction, in generated code").
- The evaluation table in Section 5 (the empirical numbers were measured
  end-to-end against a locally generated project running Qwen 2.5 3B via
  Ollama; reproducible from the public repository).

## File hygiene

After Overleaf compilation, you may end up with auxiliary files
(`*.aux`, `*.log`, `*.bbl`, `*.blg`, `*.out`, `*.synctex.gz`). These are
build artifacts and should not be committed.

For local builds, add them to `.gitignore`:

```
paper/*.aux
paper/*.log
paper/*.bbl
paper/*.blg
paper/*.out
paper/*.synctex.gz
paper/main.pdf
```
