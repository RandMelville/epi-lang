# Epi v0.3 — Limitations

This document enumerates, without softening, what Epi v0.3 does **not** do and
where the project is weak. It exists because honest documentation outperforms
defensive marketing: contributors, reviewers, and potential adopters deserve
to know the failure modes before they invest time.

If you are evaluating Epi for production use, read this file before the
README.

---

## Scope

Epi proposes a type discipline that makes the epistemic boundary between
deterministic computation (`Rigid`) and stochastic inference (`Epistemic`)
explicit at the language level, and packages that discipline as a transpiler
that emits auditable-by-construction code. It is most useful in domains where
hallucination must be **contained by contract**, not merely mitigated by
convention — e.g., pedagogical assessment, regulated workflows, structured
extraction with mandatory human review, and any system where an LLM output
must be type-bound and traceable.

Outside that target, Epi is overhead.

---

## When NOT to use Epi

Epi is the wrong tool when:

- **Conversational chatbots and customer-support assistants.** The whole
  point of a chatbot is open-ended dialogue. Epi's `confidence` thresholds,
  `checkpoint` blocks, and `Trace` records add ceremony with no payoff if the
  output is a free-form reply.
- **Complex RAG pipelines, fine-tuning workflows, or multi-tool agents.** Epi
  v0.3 has no first-class model of retrieval, tool calls, or agent loops. You
  can wire them by hand in the generated code, but you lose most of the
  type-discipline argument in the process. LangGraph, LlamaIndex, and the
  Vercel AI SDK model these scenarios better today.
- **Teams with a mature in-house AI platform.** If your organization already
  runs a vetted LangGraph/LangChain/custom orchestration layer, adopting a
  DSL is migration cost, not leverage.
- **Pure creative generation (poetry, fiction, image prompts, art).**
  `confidence` and `checkpoint` presuppose a ground truth or a reviewer
  judgment about correctness. Aesthetic outputs have neither. Forcing them
  into the Epi type system produces noise.
- **Sub-100ms latency budgets with no human-in-the-loop tolerance.** A
  `checkpoint` block is a blocking review gate. If your SLO does not allow
  for it and you also cannot ship without it, Epi is not your tool.
- **Large teams where DSL learning cost exceeds library cost.** A team of
  forty engineers learning a new `.epi` syntax is a measurable productivity
  hit. A well-typed library in TypeScript or Python may serve them better.

---

## Current implementation limitations

These are concrete deficiencies of the v0.3 transpiler and runtime. No
apology, just the list.

- **Single LLM provider, hard-coded.** The generated Next.js code targets
  Anthropic Claude (currently Sonnet 4) via the official SDK. The type
  system is provider-agnostic by design — `Epistemic` is a discipline, not
  an API binding — but the code generator is not. A multi-provider adapter
  (Ollama, OpenAI, Anthropic, possibly Gemini) is scheduled for v0.4.
- **FastAPI target is experimental and gated.** The CLI intentionally
  blocks `--target fastapi` until the Python backend reaches feature parity
  with the Next.js generator. Today, only `--target nextjs` produces a
  complete, runnable project.
- **`Lens.Mood` is a deterministic keyword lookup, not an LLM call.** The
  `Mood: "Clean, Educational"` annotation maps a small set of keywords to
  Tailwind class bundles (six hard-coded moods). It does **not** invoke a
  model. Whether to keep this surface (and lift it into the type system
  properly) or remove it entirely is an open epistemological question for
  v0.4. Today it is honest to call it a sugar layer, not an Epistemic feature.
- **Database backend is PostgreSQL-only.** The generated project assumes
  Prisma over PostgreSQL. There is no SQLite path for quick local
  experimentation, which raises the floor for new users.
- **No LSP, no syntax highlighting, no formatter.** Editors treat `.epi` as
  plain text. There is no `epi fmt`, no diagnostic server, no IDE plugin.
  Writing Epi code today means writing it in a generic text editor and
  relying on the transpiler's error messages.
- **No incremental compilation, no watch mode.** Each `epi build` is a full
  regeneration of the target project. Acceptable at v0.3 scale, painful at
  larger scale.
- **Error messages are utilitarian, not pedagogical.** The transpiler reports
  parse and type errors but does not yet match the diagnostic quality of
  mature compilers (Rust, Elm). Improving this is a v0.4+ task.

---

## Formal verification limitations

The paper and SPEC make claims about epistemic soundness. The current state
of those claims is:

- **Theorem 1 (Epistemic Soundness) is an informal proof sketch**, not a
  formal theorem. It argues, in prose, that a well-typed Epi program cannot
  silently confuse a `Rigid` value with an `Epistemic` one. This level of
  rigor is adequate for venues such as SBLP, PLATEAU, and Onward!
  Essays/Papers. It is **not** sufficient for PLDI, POPL, or ICFP.
- **No mechanized proofs.** Nothing in Coq, Isabelle, Lean, or Agda. Future
  work, explicitly.
- **Type system semantics are described informally.** SPEC.md describes the
  typing rules in prose plus a handful of judgment-style fragments. There is
  no full operational semantics, no denotational model, and no proven type
  safety result.
- **No subject reduction / progress proof.** Standard PL machinery is absent.
- **`Trace` and `Checkpoint` are specified operationally**, not denotationally.
  Their meaning is "what the generated runtime does," not a mathematical
  object independent of the implementation.

If you came here from a PL theory background expecting a fully formalized
calculus: this is not that, yet. It is a language design with a credible
type-system intuition and a working transpiler.

---

## Empirical limitations

- **Single author. No external production users as of v0.3.** Bus factor:
  one. There is no second maintainer with commit rights, no organization
  backing, and no production deployment outside the author's own work.
- **No empirical comparison study yet.** There is no published study
  comparing Epi-generated code against hand-written equivalents on metrics
  such as defect rate, hallucination incidents, review time, or developer
  experience. A study is in progress for v0.4.
- **Examples are illustrative, not benchmarked.** The `examples/` directory
  contains pedagogical-assessment and contract-review programs that are
  domain-realistic, but they have not been validated as statistically
  representative of the target domain. Treat them as walkthroughs, not
  evidence.
- **No performance benchmarks** for transpilation time, generated-code
  startup, or per-request overhead of `Trace` and `Checkpoint`.

---

## Community and adoption

- **No npm package, no conda package.** Distribution is PyPI-only
  (`pip install epi-lang`). JavaScript-ecosystem users cannot install via
  their native tooling.
- **No public Discord, Slack, or forum.** Discussion happens in GitHub
  issues or directly with the author. There is no community channel.
- **No external examples.** Everything in `examples/` was written by the
  author. There is no third-party gallery.
- **Documentation is English-first.** Portuguese translations exist but lag
  the English source. Other languages are unsupported.
- **No video tutorials, no conference talks recorded.** The SBLP 2026
  submission, if accepted, will be the first public talk.

---

## What we will fix in v0.4

The following items are committed for the v0.4 milestone (not "maybe,"
not "future work — actually scheduled"):

- **Multi-provider adapter** (Ollama, OpenAI, Anthropic, possibly Gemini),
  selectable per-project or per-`Epistemic` block.
- **`epi init` command** for project bootstrap without manual scaffolding.
- **Empirical study results**: the v0.4 release will ship alongside a
  comparison study against hand-written baselines.
- **`Lens.Mood`: formal decision.** Either lift it into the type system
  with proper semantics, or remove it. The current keyword-lookup
  half-measure will not survive v0.4.
- **SQLite support** for quickstart with zero database setup.
- **FastAPI target out of experimental** with feature parity to the Next.js
  generator.

Items explicitly **not** committed for v0.4: LSP, mechanized proofs, agent
modeling, retrieval primitives. Those are v0.5 and beyond, if at all.

---

## A note on honest critique

If you find a gap not listed here, please open an issue at
**github.com/RandMelville/epi-lang/issues** with the label `limitation`.

The project's working assumption is that honest critique is more valuable
than wishful documentation. A limitation we know about is a limitation we
can decide what to do with. A limitation hidden in marketing copy is a
trap for the next contributor.

— Randerson Rebouças, author, Epi
