<!--
================================================================
DRAFT FOR INTERNAL REVIEW — NOT YET ANONYMIZED FOR DOUBLE-BLIND
================================================================

Target venue:    SBLP 2026 — Short Paper track
Page limit:      4 pages (excluding references)
Language:        English (encouraged by the CFP)
Review process:  Double-blind (will require removing names, affiliations,
                 acknowledgments, and rewriting self-citations in third
                 person BEFORE submission via JEMS3).
Submission:      https://jems3.sbc.org.br/events/462
Deadline:        1 June 2026 (firm, no extensions)
Template:        Overleaf (https://www.overleaf.com/read/cyhpwwkngcwk)

Authors of this draft (NOT in final submission text — those go in JEMS3 metadata):
  - Randerson Rebouças       — UFRGS / PPGIE
  - Prof. Dante Barone       — UFRGS
  - [Prof. Eliseo Reátegui — pending invitation acceptance]

When submitting, replace authorial information with "Anonymous" in the
manuscript and put real authors only in JEMS3 metadata.

Word budget (approx., for SBC 4-page template):
  Abstract:                    ~180 words
  §1 Introduction:             ~600 words  (~0.75 page)
  §2 Background & Related Work:~400 words  (~0.5  page)
  §3 Epistemic Type System:    ~700 words  (~0.85 page)
  §4 Transpiler Architecture:  ~400 words  (~0.5  page)
  §5 Empirical Evaluation:     ~600 words  (~0.75 page)
  §6 Discussion & Limitations: ~250 words  (~0.3  page)
  §7 Conclusion:               ~150 words  (~0.2  page)
  Total body:                  ~3100 words  (~3.9 pages, fits 4-page limit)
-->

# Epi: An Epistemic Type System for Containing LLM Hallucination in Generated Code

**Randerson Rebouças**, **Dante Barone**
*Postgraduate Program in Informatics in Education (PPGIE), UFRGS, Brazil*
`randerson.melville@gmail.com` · `barone@inf.ufrgs.br`

> **For double-blind submission, replace the byline above with**
> *"Anonymous, Anonymous Affiliation"* — author identities go to JEMS3 metadata only.

---

## Abstract

We introduce **Epi**, a domain-specific language whose type system makes the boundary between deterministic computation and LLM-inferred values explicit and enforceable. From a single `.epi` source describing entities, authorization rules, AI inference steps, and orchestration pipelines, the Epi transpiler emits a complete runnable Next.js project — database schema, API routes, authorization middleware, runtime validators, LLM call wrappers, and human-review checkpoints. Every AI-inferred field carries a type-level contract — an enum, a numeric range, a confidence threshold, an optional Bayesian prior — that the transpiler enforces in the generated code. The developer does not write the validation; the type requires it. We argue that LLM hallucination cannot be prevented but can be *contained* at the type-system boundary, by construction, in generated code. We evaluate Epi end-to-end using the same `.epi` source compiled against Anthropic Claude (cloud) and Qwen 2.5 3B (local via Ollama). On an educational assessment task, the boundary correctly routes a low-confidence misclassification to teacher review — a behavior that is a structural consequence of a type annotation, not handwritten code. Epi is open-source under Apache 2.0.

**Keywords:** type systems · domain-specific languages · LLM applications · code generation · information-flow control

---

## 1. Introduction

Large Language Models (LLMs) are increasingly embedded in production software, performing classification, extraction, summarization, and generation alongside conventional business logic. Yet the languages we use to build that software were designed in an era when all computation was deterministic: a function given the same input is expected to produce the same output. This assumption silently fails the moment an LLM enters the call graph.

We identify three concrete problems that arise when building LLM-augmented applications in conventional languages.

**P1 — No type-level separation of epistemic domains.** A database column declared as `status: String` and an LLM-inferred column declared as `risk: String` are treated identically by the host type system. If the LLM hallucinates `"Unknown"` instead of one of the expected labels, the value lands in the database with no type-level alarm.

**P2 — Forced stack fragmentation.** Building a single AI-augmented feature requires the developer to hold multiple mental models simultaneously: SQL or Prisma for the database, TypeScript or Python for the API layer, React for the user interface, and a vendor SDK for the LLM. One conceptual decision boundary is distributed across four grammars and four toolchains.

**P3 — No grammar-enforced hallucination contract.** Output validation, retry strategies, confidence thresholding, fallback dispatch, and audit trails are all *optional* features that the developer must remember to add. In practice, in our experience and in conversations with practitioners, they are routinely forgotten.

This paper introduces **Epi (Epistemic Programming Interface)**, a domain-specific language and transpiler that addresses these problems together. Our contributions are fourfold:

1. The **Epistemic Type System**, a type discipline that separates *rigid* (deterministic) and *epistemic* (AI-inferred) values at the type level and requires runtime validation at the boundary by construction;
2. The **Epi language**, with five orthogonal primitives (Entity, Guard, Pulse, Pipeline, Lens) and a Lark/EBNF grammar;
3. The **Epi transpiler**, a three-layer architecture in which the LLM is formally excluded from the deterministic layers and operates only within constraints emitted by them;
4. An **end-to-end empirical demonstration** showing that the same `.epi` program runs against a frontier cloud LLM and a small local open-weight model, and that the type system catches a low-confidence misclassification exactly where the type contract requires.

The thesis is narrow and we state it explicitly: **LLM hallucination cannot be prevented, but it can be contained at a type-system boundary, by construction, in generated code.**

## 2. Background and Related Work

Epi sits at the intersection of three lines of work in programming languages and verification.

**Information-flow control.** The Rigid/Epistemic distinction is structurally analogous to the type-level separation of security levels in information-flow analyses. Russo and Sabelfeld [11] contrast dynamic and static flow-sensitive analyses, both of which encode non-interference between value domains. Epi adapts this discipline to *epistemic provenance* — whether a value originated from deterministic code or from probabilistic inference — rather than to confidentiality levels. The transpiler enforces non-interference by emitting validation at every domain crossing.

**Probabilistic programming.** Probabilistic Programming Languages such as ProbZelus [2] and SlicStan [4] embed probability distributions as first-class language constructs and distinguish deterministic from probabilistic computation. Epi draws inspiration from this lineage but operates at a different layer: application orchestration of pre-trained model endpoints, not implementation of inference algorithms.

**Typed LLM signatures and full-stack DSLs.** BAML [3] provides typed signatures for LLM functions, and DSPy [6] compiles declarative signatures into optimized prompts. Both work at the level of individual LLM calls. Epi extends typed LLM signatures to *whole-application generation*, including database, middleware, validators, and UI scaffolding. Wasp [13] is a full-stack DSL targeting React + Node without distinguishing AI-inferred values. Epi's distinguishing mechanism over these systems is the epistemic type discipline, which makes audit-by-construction a structural consequence of the type rather than a feature the developer can omit.

## 3. The Epistemic Type System

In Epi, every value belongs to one of two type domains.

**Rigid types** are deterministic and have no AI involvement:

```
UUID  Text  Int  Float  Decimal  Bool  DateTime  JSON
```

**Epistemic types** are AI-inferred and carry mandatory validation parameters:

```
AI.Enum(values..., strict, prior, confidence_threshold)
AI.Text(max_tokens)
AI.Classification(labels)
AI.Score(min, max)
AI.Embedding(dimensions)
```

A field declared with an epistemic type imposes obligations on the generated code. Consider:

```epi
risco: AI.Enum(Alto, Medio, Baixo,
               strict: true, confidence_threshold: 0.85)
```

This single declaration requires the transpiler to emit, in the output project, four artifacts:

1. A **database column** of compatible storage type;
2. A **runtime validator** (a Zod schema in TypeScript output) that rejects values outside the declared enum;
3. An **LLM inference call** wrapped to return JSON containing the value and a `_confidence` field in $[0, 1]$;
4. A **confidence-aware dispatch**: if reported confidence is below the threshold, route to a Checkpoint endpoint for human review; otherwise validate and persist.

None of these artifacts is optional. A type-correct Epi program cannot omit any of them because the type forces their emission. This is the central design choice: the *type carries an obligation that the transpiler discharges in the generated code*. In Pierce's terms [9], the type system rules out a class of programs — those that persist unvalidated AI output — by making them inexpressible.

**The five primitives.** Programs are composed of **Entity** declarations (typed schemas), **Guard** declarations (authorization predicates over the request context), **Pulse** declarations (AI execution units with prompt files, temperature, fallback strategies), **Pipeline** declarations (composed Pulse flows with error policies), and **Lens** declarations (UI surface descriptors). Of these, only Pulse and the epistemic fields within Entity invoke the AI; the others are deterministic.

**Trace and Checkpoint.** A Pulse may decompose into a sequence of *Trace* steps. Each Trace can `Expose` intermediate reasoning fields and pause at a `Checkpoint` for human review before the next step proceeds. The transpiler emits an inspect/resume HTTP API and a persistent audit trail of each approval or correction. This mechanism is intended for high-stakes flows — educational assessment, clinical pre-screening, legal triage — where reasoning must be auditable, not only the final outcome.

**Bayesian update.** An `AI.Enum` field may declare a prior distribution over its labels. The transpiler emits a `bayesianUpdate<Entity><Field>` function that combines the prior with the model's reported likelihoods via Bayes' rule, producing a normalized posterior and a confidence summary. This couples model output with domain knowledge of the base rates, rather than overwriting it.

## 4. Transpiler Architecture

The Epi transpiler is organized in three layers:

```
.epi source
   ▼
[Layer 1: Parser]              Lark + EBNF — 100% deterministic
   ▼
[Layer 2: Rigid Generator]     Prisma schema, middleware, routes,
                               Zod validators — 100% deterministic
   ▼
[Layer 3: Epistemic Generator] LLM call wrappers, Trace + Checkpoint,
                               Bayesian update — operates only within
                               contracts emitted by Layer 2
```

The LLM is formally excluded from Layers 1 and 2; the deterministic layer encodes the constraints, and the epistemic layer can only operate within them. The structural similarity to the *standard library / user code* split in mainstream type-system implementations is intentional: the constraints are not a runtime check appended after the fact, but a compile-time guarantee that the runtime cannot violate without failing closed.

**Provider-agnostic LLM client.** Layer 3 emits a single file, `lib/llm-client.ts`, that abstracts the LLM provider behind a uniform `llmCall(params)` interface. Runtime environment variables (`EPI_AI_PROVIDER`, `EPI_AI_MODEL`, `EPI_AI_BASE_URL`) select between Anthropic Claude and any OpenAI-compatible endpoint; we target Ollama [8] for local open-weight models. The epistemic contract — JSON output containing a `_confidence` field, parseable by the Zod schema — is enforced uniformly across providers. The choice of provider is a deployment concern, not a code change.

## 5. Empirical Evaluation

We exercise an educational scenario end-to-end. The `.epi` source declares one Entity `Submissao` (student answer) with an epistemic field `avaliacao: AI.Enum(Correto, Parcial, Incorreto, prior: Distribution(0.40, 0.45, 0.15), confidence_threshold: 0.85)`, one Guard for teacher authentication, one Pulse `AvaliarResposta` invoking `AI.classify` with `on_low_confidence: Checkpoint.ReviewRequired(role: "Professor")`, and one Pipeline. The full source is 30 lines; the transpiled project contains 13 files comprising approximately 700 lines of TypeScript and Prisma schema.

We compile the same `.epi` source twice and exercise both deployments without modification: (a) against **Anthropic Claude Sonnet 4** (cloud); (b) against **Qwen 2.5 3B Instruct** (Q4_K_M, ~1.9 GB) running locally via Ollama on consumer hardware (Apple Silicon, 16 GB RAM). The only difference is the value of `EPI_AI_PROVIDER` in the deployment's `.env` file. We submit three student answers to the prompt "What is photosynthesis?":

| Student answer | Qwen 2.5 3B output | Boundary action | Latency |
|---|---|---|---|
| Textbook-correct full definition | `{"avaliacao":"Parcial", "_confidence":0.8}` | $0.8 < 0.85$ → **Checkpoint dispatched to Professor** | 2.6 s |
| "Plants eat sunlight." | `{"avaliacao":"Incorreto", "_confidence":0.9}` | Validated → `"Incorreto"` persisted | 0.8 s |
| "Photosynthesis is my dog's name." | `{"avaliacao":"Incorreto", "_confidence":0.9}` | Validated → `"Incorreto"` persisted | 0.8 s |

**Observation.** The first row is the contribution. A textbook-correct answer was misclassified by the small model as `"Parcial"` — a false negative that, persisted, would unfairly affect the student. The model's own reported confidence (0.8) fell below the type-declared threshold (0.85). The transpiler-emitted dispatch routed the case to a human reviewer *before* persistence. **The developer wrote no code for this behavior.** It is a structural consequence of the `confidence_threshold: 0.85` annotation in the type, which the transpiler discharged in Layer 3.

**Provider parity.** Submitting the same three inputs against Anthropic Claude Sonnet 4 returned the textbook-correct answer as `"Correto"` with confidence above 0.9, validating directly. The pipeline behaves identically at the boundary against both providers; the differences are absolute accuracy and latency. This confirms that the epistemic contract is enforced independently of the inference engine — provider-agnosticism is not a claim, it is a verified property of the generated code.

**Hallucination containment.** In a separate run, we induced a malformed JSON output from the local model. The Zod schema rejected the value and the transpiler-emitted fallback (`Fallback.ManualReview`) routed the request to a manual queue. Again, no handwritten error path was required.

## 6. Discussion and Limitations

**Type-system formalization.** The current type-system specification is informal: we present an executable transpiler and an empirical demonstration, but not a mechanized soundness proof. The property we informally describe — *every epistemic value is validated against its declared schema before persistence* — is a non-interference property between rigid and epistemic value spaces. A formal treatment in Coq or Agda is future work.

**Coverage of targets.** The transpiler currently emits a complete Next.js project. A FastAPI target is partially implemented and intentionally gated in the CLI until complete. This is an engineering limitation, not an essential property of the design.

**Empirical scope.** We report results from a single educational scenario. A controlled empirical study comparing Epi-generated applications against hand-written equivalents — in terms of correctness coverage, audit completeness, and developer time — is planned for the next phase.

**Lens.Mood.** The Lens primitive includes a `Mood` declaration that currently maps keywords to UI utility classes via a deterministic lookup table. This is the weakest part of the current design and is documented as experimental.

## 7. Conclusion

LLM hallucination is a property of the underlying inference, not of the surrounding code. It cannot be prevented at the type-system level. It can, however, be **contained**: a type discipline that distinguishes deterministic from epistemic provenance can require — by construction, in generated code — that every AI-inferred value pass through a validator, report its confidence, and surface for human review when uncertain. We have implemented this discipline as a language and a transpiler, demonstrated it end-to-end against both a frontier cloud model and a small local model, and shown that the boundary catches a misclassification that would otherwise propagate into a database of record. The implementation is open source and packaged for distribution.

---

## References

> **Note:** numbers in brackets in the text refer to this list. In the LaTeX
> version, switch to `\bibliographystyle{sbc}` and `\bibliography{epi}` with
> a `epi.bib` file. The list below is intentionally tight (the SBLP short
> paper has a 4-page text limit but unlimited references; we keep a small
> set of high-relevance citations).

[1] **Anthropic.** *Claude API documentation*. anthropic.com/api, 2025.

[2] **Baudart, G., Mandel, L., Atkinson, E., Sherman, B., Pouzet, M., Carbin, M.** Reactive Probabilistic Programming. *PLDI 2020*, 898–912.

[3] **BoundaryML.** *BAML: a domain-specific language for AI engineering.* github.com/BoundaryML/baml, 2024.

[4] **Gorinova, M.I., Gordon, A.D., Sutton, C.** Probabilistic Programming with Densities in SlicStan: Efficient, Flexible, and Deterministic. *POPL 2019*.

[5] **Hatch.** *Hatchling build backend.* hatch.pypa.io.

[6] **Khattab, O., Singhvi, A., Maheshwari, P., et al.** DSPy: Compiling Declarative Language Model Calls Into Self-Improving Pipelines. *arXiv:2310.03714*, 2023.

[7] **Lark.** *Lark — a parsing toolkit for Python.* github.com/lark-parser/lark.

[8] **Ollama Inc.** *Ollama: run open-weight LLMs locally.* ollama.com, 2024.

[9] **Pierce, B.C.** *Types and Programming Languages.* MIT Press, 2002.

[10] **Prisma.** *Prisma ORM documentation.* prisma.io.

[11] **Russo, A., Sabelfeld, A.** Dynamic vs. Static Flow-Sensitive Security Analysis. *CSF 2010*, 186–199.

[12] **Vercel.** *Next.js framework.* nextjs.org.

[13] **Wasp.** *Wasp — a DSL for full-stack web apps.* wasp-lang.dev, 2024.

[14] **Zod.** *TypeScript-first schema validation.* zod.dev.

---

<!--
================================================================
NOTES FOR THE CO-AUTHORS (to be removed before submission)
================================================================

1. Anonymization checklist before JEMS3 submission:
   - Replace the byline with "Anonymous"
   - Remove the affiliation line
   - Remove footnote references to UFRGS / PPGIE
   - Convert phrases like "in our experience" or "we developed" that
     identify the team to neutral phrasings, OR explicitly cite
     [Author 2026] for the implementation as if it were prior work.
   - Replace explicit URL "github.com/RandMelville/epi-lang" with
     "Anonymous repository available with the supplementary material"
     or similar.
   - Remove the project website URL.

2. Sections that may need expansion if space allows:
   - Section 3 — type rules in formal notation (currently described
     prose-style). Could add a small judgement-rule table.
   - Section 5 — second comparative table for Claude outputs alongside
     the Qwen outputs, side-by-side.

3. Sections that may need contraction if 4-page limit is tight:
   - Section 1 — combine P1/P2/P3 into a single paragraph.
   - Section 2 — drop SlicStan and DSPy if pressed for space; keep
     Russo & Sabelfeld and ProbZelus as primary anchors.

4. Open questions for co-authors:
   - Title: "Epi: An Epistemic Type System for Containing LLM Hallucination
     in Generated Code" — too long? Alternatives:
       (a) "Containing LLM Hallucination at a Type-System Boundary"
       (b) "Epi: Type-Driven Generation of AI-Augmented Applications"
       (c) "Type Discipline for AI-Augmented Code: The Epi Language"
   - Should we frame the contribution as "language design" or as
     "tool paper"? Currently mid-way. SBLP short-paper track allows both.
   - Bayesian update: keep in §3 or move to §5 as concrete artifact?

5. Pending verification with co-authors (Prof. Dante, Prof. Eliseo):
   - Authorship order
   - Whether to cite Russo & Sabelfeld (Prof. Fernando Magno's
     suggestion) as the primary related-work anchor or as one of many.
   - Whether to acknowledge Prof. Rosa Maria Vicari (PPGIE) for the
     conceptual origin of Trace + Checkpoint — only in the final
     non-anonymized version, in Acknowledgments.
-->
