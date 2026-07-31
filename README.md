<p align="center">
  <strong>Epi</strong> — Epistemic Programming Interface
</p>

<p align="center">
  <em>A type discipline for AI-augmented full-stack applications</em>
</p>

<p align="center">
  <a href="https://github.com/RandMelville/epi-lang/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License"></a>
  <a href="https://pypi.org/project/epi-lang/"><img src="https://img.shields.io/pypi/v/epi-lang?color=orange" alt="PyPI"></a>
  <img src="https://img.shields.io/badge/python-%3E%3D3.11-blue.svg" alt="Python">
  <a href="https://doi.org/10.5281/zenodo.21433256"><img src="https://zenodo.org/badge/DOI/10.5281/zenodo.21433256.svg" alt="DOI"></a>
  <a href="https://cbsoft.sbc.org.br/2026/"><img src="https://img.shields.io/badge/SBLP%202026-Accepted-success.svg" alt="Accepted at SBLP 2026"></a>
</p>

---

> **Research status:** v0.3 — active development, structural validation phase.
>
> Authors: [Randerson Rebouças](https://github.com/RandMelville) (PhD candidate, UFRGS), Dante Barone, and Eliseo Reátegui, PPGIE/UFRGS.
> The short paper **"Epi: An Epistemic Type System for Containing LLM Hallucination in Generated Code"** was **accepted at SBLP 2026**, the 30th Brazilian Symposium on Programming Languages, part of [CBSoft 2026](https://cbsoft.sbc.org.br/2026/).
>
> **Accepted paper:** [paper/Epi-SBLP2026-camera-ready.pdf](paper/Epi-SBLP2026-camera-ready.pdf) (camera-ready). This repository is the artifact for that paper; the archived snapshot is at [doi.org/10.5281/zenodo.21433256](https://doi.org/10.5281/zenodo.21433256).

## What Epi is

Epi is a domain-specific language whose type system makes the **epistemic boundary** between deterministic computation and AI inference explicit. From a single `.epi` source, the transpiler generates a complete Next.js project — database schema, API routes, auth middleware, runtime validators, LLM inference calls, and UI components — such that **AI-inferred values cannot bypass validation**.

The thesis is narrow and honest: LLM hallucination cannot be prevented, but it can be **contained at a type-system boundary, by construction, in the generated code**.

## What problem this solves

In a typical AI-augmented app, validation of LLM outputs, confidence thresholding, fallback handling, and audit trails are all **optional** — features the developer must remember to add. They get omitted in practice.

Epi makes them **structural consequences of the type**. A declaration like

```epi
risco: AI.Enum(Alto, Medio, Baixo, strict: true, confidence_threshold: 0.85)
```

necessarily produces:

1. A database column (deterministic, Prisma).
2. A Zod schema constraining the LLM output at runtime.
3. An LLM inference call with confidence reporting.
4. A checkpoint route that pauses for human review when confidence is below threshold.

You cannot compile an Epi program with an AI field and forget to validate the output. The transpiler emits the contract.

## Example

```epi
@Language: Epi v0.3
@Goal: "Contract Analysis with Human-in-the-loop"

Entity Contrato {
    id: UUID(auto),
    titulo: Text,
    documento: Text,
    valor: Decimal,
    criado_em: DateTime(auto),
    risco: AI.Enum(Alto, Medio, Baixo, strict: true)
}
//       ▲ Rigid: deterministic    ▲ Epistemic: AI-inferred, validated at the boundary

Guard SomenteAdvogados {
    Condition: Auth.Role == "Lawyer"
}

Pulse ExtrairRisco {
    Input: Contrato
    Protect: Guard.SomenteAdvogados
    Process:
        Execute: AI.scan(
            source: Input.documento,
            prompt: file("@prompts/legal_scan.md"),
            temperature: 0.1,
            on_fail: Fallback.ManualReview(Queue: "Advogados")
        )
    Output: Contrato.risco
}

Pipeline AnalisarContrato {
    Flow: ExtrairRisco -> GerarResumo -> Notificar
    On_Error: Retry(max: 3, backoff: exponential)
}

Lens Dashboard {
    Mood: "Clean, Legal-Tech"            // [experimental]
    Display:
        Table(Contrato, columns: [titulo, valor, risco]),
        Form(Contrato) -> Button("Analisar").trigger(ExtrairRisco)
}
```

Fewer than 80 lines. The transpiler generates the entire Next.js project — schema, middleware, routes, validators, LLM calls, UI — with the epistemic contract enforced.

## When to use Epi

- Domains where audit-by-construction is required: legal, healthcare, education, government.
- Apps where AI-inferred values must be persisted and traceable, not just shown.
- Focused LLM-augmented products, not general-purpose AI platforms.
- Settings where human-in-the-loop is structural (Trace + Checkpoint maps naturally).
- Domains with a meaningful prior distribution (Bayesian update genuinely helps).

## When NOT to use Epi

- Conversational chatbots or customer-support assistants.
- Apps centered on complex RAG, multi-tool agents, or fine-tuning workflows.
- Teams with a mature in-house AI platform (LangGraph custom, internal orchestration).
- Pure creative generation (`confidence` and `checkpoint` don't apply).
- Latency-critical paths under 100 ms; Epi is for decision-grade flows.

See [docs/LIMITATIONS.md](docs/LIMITATIONS.md) for the full honest list of gaps in v0.3.

## Architecture

A three-layer transpiler. The LLM is formally excluded from Layers 1 and 2.

```
.epi source
   ▼
[Layer 1: Parser]            Lark + EBNF              100% deterministic
   ▼
[Layer 2: Rigid Generator]   Prisma, middleware,      100% deterministic
                             routes, Zod validators
   ▼
[Layer 3: Epistemic Gen.]    LLM calls, Trace,        validated by Layer 2
                             Checkpoint, Lens
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full breakdown.

## Requirements

To run the transpiler:

| | Version | Notes |
|---|---|---|
| Python | >= 3.11 | the Epi CLI and transpiler |
| pip | any recent | `pip install epi-lang` |

To build and run a project the transpiler generates:

| | Version | Notes |
|---|---|---|
| Node.js + npm | >= 20 | the emitted project is Next.js |
| PostgreSQL | >= 14 | or any `DATABASE_URL` Prisma accepts |
| An LLM provider | | either an Anthropic API key, or [Ollama](https://ollama.com) running locally. Neither is needed to validate or transpile, only to execute the generated AI calls. |

To reproduce the containment evaluation of the paper (`eval/`):

| | Notes |
|---|---|
| Ollama | serving `qwen2.5:3b-instruct` and `llama3.2:1b`, about 3.5 GB on disk together |
| RAM | 16 GB is what the reported numbers were measured on |

Developed and measured on macOS 15 (Apple Silicon, 16 GB RAM). Nothing in the
toolchain is platform-specific, but no other platform has been exercised.

## Installation

```bash
pip install epi-lang
```

Or from source, which is also what you need for the example programs and the
evaluation harness:

```bash
git clone https://github.com/RandMelville/epi-lang.git
cd epi-lang
pip install -e ".[dev]"
```

### Check that it works

The fastest end-to-end check needs no database, no API key and no Node:

```bash
epi validate examples/avaliacao-simples.epi
epi transpile examples/avaliacao-simples.epi --outdir ./generated
ls generated
```

That parses the program of Section 5 of the paper and writes the generated
project (13 files, 477 lines) to `./generated`. The full test suite:

```bash
pytest
```

### Run a generated project

```bash
cd generated
npm install
cp .env.example .env
# Set DATABASE_URL, then pick a provider:
#   EPI_AI_PROVIDER=anthropic + ANTHROPIC_API_KEY=sk-ant-...
#   EPI_AI_PROVIDER=ollama    (requires `ollama serve`)
npx prisma migrate dev --name init
npm run dev
```

### Reproduce the paper's evaluation

```bash
cd eval
./setup.sh
```

See [eval/README.md](eval/README.md) for the harness, the 40-item dataset with
gold labels, and the raw per-call results behind Table 2.

## The five primitives

| Primitive | What it does | Status |
|---|---|---|
| **Entity** | Data schema with typed fields, rigid + epistemic | stable |
| **Guard** | Auth & authorization, transpiles to middleware | stable |
| **Pulse** | AI execution unit with `temperature`, `prompt`, `on_fail` | stable |
| **Pipeline** | Composes Pulses with retry/backoff strategy | stable |
| **Lens** | Semantic UI declaration | `Display` / `Inject` stable; `Mood` experimental |

## The epistemic type system

Two domains.

**Rigid types** — deterministic, no AI involvement:

```
UUID(auto)   Text   Int   Float   Decimal   Bool   DateTime(auto)   JSON
```

**Epistemic types** — AI-inferred, runtime-validated:

```
AI.Enum(values..., strict, prior, confidence_threshold)
AI.Text(max_tokens)
AI.Classification(labels)
AI.Score(min, max)
AI.Embedding(dimensions)
```

A single epistemic declaration generates a database column, a Zod validator, an LLM inference call, and optionally a checkpoint route. If it compiles, the runtime contract is enforced.

## Trace + Checkpoint (v0.3 highlight)

A `Pulse` can be decomposed into `Trace` steps. Each step can `Expose:` intermediate reasoning fields and pause at a `Checkpoint:` for human review before the final output is committed.

```epi
Pulse AvaliarRespostaAluno {
    Trace CompreenderEnunciado {
        Execute: AI.reason(source: Input.enunciado, prompt: file("@prompts/..."))
        Expose: interpretacao, conceitos_chave, criterios_avaliacao
        Checkpoint: ReviewRequired(role: "Professor")
    }

    Trace AvaliarResposta {
        Execute: AI.classify(
            source: Input.resposta_aluno,
            confidence_threshold: 0.85,
            on_low_confidence: Checkpoint.ReviewRequired(role: "Professor")
        )
    }
}
```

This generates an in-memory `TraceState` store, inspect / resume HTTP routes, and an audit trail of every human approval or correction. Designed for high-stakes evaluation flows (pedagogical assessment, legal review, clinical triage).

## Documentation

| Document | Purpose |
|---|---|
| [docs/SPEC.md](docs/SPEC.md) | Formal language specification (English, canonical) |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Transpiler architecture and design decisions |
| [docs/MANIFESTO.md](docs/MANIFESTO.md) | Why epistemic types matter |
| [docs/LIMITATIONS.md](docs/LIMITATIONS.md) | What Epi does NOT do (honest list of gaps) |
| [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) | How to contribute |
| [paper/Epi-SBLP2026-camera-ready.pdf](paper/Epi-SBLP2026-camera-ready.pdf) | **The accepted SBLP 2026 paper** (camera-ready) |
| [paper/main.tex](paper/main.tex) | LaTeX source of the accepted paper |
| [docs/PAPER.md](docs/PAPER.md) | Early internal draft, unpublished and superseded by the paper above, not kept in sync |
| [docs/translations/SPEC-PT.md](docs/translations/SPEC-PT.md) | Portuguese translation (may lag) |

## Status

**Stable in v0.3:**
- EBNF grammar (Lark)
- AST with epistemic type system (Pydantic)
- Parser + Lark transformer
- Deterministic generators: Prisma schema, middleware, routes, Zod validators
- Epistemic generators: LLM calls, Trace + Checkpoint, Bayesian prior
- Provider-agnostic LLM client in the generated project: Anthropic, or any
  OpenAI-compatible endpoint, with Ollama used for local open-weight models.
  Selected by `EPI_AI_PROVIDER` at deployment, with no change to the `.epi` source.
- CLI: `validate`, `parse`, `transpile`
- 127 tests passing (`pytest`)
- PyPI package (`pip install epi-lang`)

**Experimental — known to be incomplete:**
- `Lens.Mood` — deterministic keyword-to-Tailwind lookup of 6 hardcoded moods. Not LLM-generated UI; do not rely on it.
- `--target fastapi` — blocked in the CLI; current output is inconsistent.

**Planned for v0.4:**
- Gemini and a broader provider matrix on top of the existing adapter.
- `epi init` for project bootstrap without cloning the repo.
- FastAPI target completion (or formal removal).
- Empirical evaluation study (Epi-generated vs hand-written equivalents).
- SQLite option for quickstart without local Postgres.

## Related work

| System | Relationship to Epi |
|---|---|
| [ProbZelus](https://dl.acm.org/doi/10.1145/3385412.3386009) (PLDI 2020) | Separates deterministic and probabilistic reactive streams. Epi lifts the separation to application-level types. |
| [SlicStan](https://dl.acm.org/doi/10.1145/3290348) (POPL 2019) | Information-flow types for probabilistic programs. Epi adapts the discipline to AI-augmented full-stack apps. |
| Russo & Sabelfeld, *Dynamic vs. Static Flow-Sensitive Security Analysis* (CSF 2010) | Information-flow control as type-level separation of security levels — structural analog to Epi's rigid/epistemic separation. |
| [BAML](https://github.com/BoundaryML/baml) | Typed LLM function signatures. Epi extends the idea to whole-application generation. |
| [Wasp](https://wasp-lang.dev) | Full-stack DSL (React + Node). Epi adds epistemic types and AI-aware code generation. |
| [DSPy](https://dspy.ai/) (Stanford) | Declarative LLM programming via signatures. Orthogonal to Epi — DSPy optimizes prompts, Epi separates type domains. |

## Citation

```bibtex
@software{reboucas2026epi,
  author  = {Rebouças, Randerson Oliveira Melville and Barone, Dante Augusto Couto and Reátegui, Eliseo},
  title   = {Epi: An Epistemic Type System for Containing LLM Hallucination in Generated Code},
  year    = {2026},
  url     = {https://github.com/RandMelville/epi-lang},
  version = {0.3.2},
  doi     = {10.5281/zenodo.21433256}
}
```

The paper was accepted at **SBLP 2026** (30th Brazilian Symposium on Programming Languages, CBSoft 2026).

## Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md). Honest critique preferred over wishful documentation.

## License

[Apache License 2.0](LICENSE) — Copyright (c) 2026 Randerson Rebouças.
