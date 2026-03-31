<p align="center">
  <strong>Epi</strong> — Epistemic Programming Interface
</p>

<p align="center">
  <em>A Zero-Stack Intent-Oriented Language with an Epistemic Type System</em>
</p>

<p align="center">
  <a href="https://github.com/RandMelville/epi-lang/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License"></a>
  <a href="https://pypi.org/project/epi-lang/"><img src="https://img.shields.io/pypi/v/epi-lang?color=orange" alt="PyPI"></a>
  <img src="https://img.shields.io/badge/python-%3E%3D3.11-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/status-research%20%2F%20active-green.svg" alt="Status">
</p>

---

> **Research Status: Active / Structural Validation (v0.3)**
>
> Author: [Randerson Rebouças](https://github.com/RandMelville) — PhD Candidate, UFRGS

## The Problem

Modern full-stack development is a stack of accidental complexity. To build a simple application that stores data and classifies it with AI, a developer must:

1. Define a database schema (Prisma/SQL)
2. Write API routes (Express/FastAPI)
3. Add authentication middleware
4. Create validation schemas (Zod/Pydantic)
5. Wire LLM inference calls with error handling
6. Build UI components (React/Next.js)
7. Connect everything with state management

Seven layers. Three to five languages. Dozens of files. **And the actual business logic — "store a contract and classify its risk" — fits in a single sentence.**

Worse: when AI enters the picture, traditional type systems cannot distinguish between a value that was *computed* (a UUID) and a value that was *hallucinated* (an AI classification). A `string` is a `string`. The database doesn't know. The compiler doesn't care. The hallucination becomes ground truth.

## The Solution

Epi is a language with **five primitives** and an **Epistemic Type System** that formally separates what is *known* (deterministic) from what must be *inferred* (stochastic) — in the same grammar, in the same file.

You write `.epi`. The transpiler generates a complete, auditable project: database schema, API routes, auth middleware, validation schemas, LLM inference functions, and UI components.

**One file in. Full stack out. Every AI output validated.**

## How It Looks

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
//       ▲ Rigid types: deterministic    ▲ Epistemic type: AI-inferred, validated

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
    Mood: "Clean, Legal-Tech"
    Display:
        Table(Contrato, columns: [titulo, valor, risco]),
        Form(Contrato) -> Button("Analisar").trigger(ExtrairRisco)
}
```

**50 lines.** No framework boilerplate. No hand-written middleware. No untyped AI calls. The transpiler generates everything — and the Epistemic Type System guarantees that `risco` is validated against `["Alto", "Medio", "Baixo"]` before it ever touches the database.

## The Five Primitives

| Primitive | What it does | Epistemic role |
|-----------|-------------|----------------|
| **Entity** | Data schema with typed fields | Declares the epistemic boundary — rigid fields vs. AI-inferred fields |
| **Guard** | Auth & authorization constraints | Deterministic — transpiles to middleware |
| **Pulse** | AI execution with hallucination control | Epistemic — every `AI.*` call has `temperature`, `prompt`, and `on_fail` |
| **Pipeline** | Composes Pulses into flows | Deterministic — orchestration with error strategy |
| **Lens** | Semantic UI declaration | Mixed — structure is deterministic, `Mood` is epistemic |

## The Epistemic Type System

The core innovation. Every type in Epi belongs to one of two domains:

**Rigid Types** — deterministic, no AI involvement:
```
UUID(auto)  Text  Int  Float  Decimal  Bool  DateTime(auto)  JSON
```

**Epistemic Types** — AI-inferred, runtime-validated:
```
AI.Enum(Value1, Value2, strict: true)
AI.Text(max_tokens: N)
AI.Classification(labels: [...])
AI.Score(min: 0, max: 1)
AI.Embedding(dimensions: N)
```

A single `AI.Enum(Alto, Medio, Baixo, strict: true)` declaration generates:
1. A **database column** (`String` in Prisma)
2. A **runtime validation schema** (Zod enum / Pydantic validator)
3. An **LLM inference call** with temperature and fallback constraints

If it compiles, it validates.

## Architecture

Three-layer transpiler. The LLM is formally excluded from Layers 1 and 2.

```
.epi source → [Layer 1: Parser] → [Layer 2: Rigid Generator] → [Layer 3: Epistemic Generator]
               Lark + EBNF          Jinja2 templates              LLM (constrained)
               100% deterministic    100% deterministic             validated by Layer 2
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full technical breakdown.

## Quick Start

```bash
# Install from PyPI
pip install epi-lang

# Validate syntax
epi validate examples/contrato.epi

# Transpile to a full project
epi transpile examples/contrato.epi --target nextjs --outdir ./generated
```

For development:

```bash
git clone https://github.com/RandMelville/epi-lang.git
cd epi-lang
pip install -e ".[dev]"
```

## Project Structure

```
epi/grammar/epi.lark        EBNF grammar definition
epi/parser/ast_nodes.py     Pydantic AST models (Epistemic Type System)
epi/parser/builder.py       Lark Transformer (parse tree → typed AST)
epi/generators/             Code generators
  deterministic/            Layer 2: Prisma, middleware, routes
  epistemic/                Layer 3: AI inference stubs, Lens UI
epi/cli.py                  Typer CLI (parse, validate, transpile)
examples/contrato.epi       Canonical example
SPEC.md                     Formal language specification
ARCHITECTURE.md             Technical architecture
MANIFESTO.md                Project philosophy
```

## Documentation

| Document | Purpose |
|----------|---------|
| [SPEC.md](SPEC.md) | Formal language specification — grammar, type system, primitives |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Transpiler architecture — three layers, design decisions |
| [MANIFESTO.md](MANIFESTO.md) | Philosophy — why epistemic types matter |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute |

## Status

**v0.3 — Research / Active Development**

- [x] Formal specification (SPEC.md)
- [x] EBNF grammar (Lark)
- [x] AST node models (Pydantic)
- [x] Lark Transformer (parser → typed AST)
- [x] Deterministic generators (Prisma, middleware, routes with retry)
- [x] Epistemic generators (Claude API integration, fallback metadata)
- [x] Lens Mood → Tailwind styling (6 moods)
- [x] Epistemic traces + checkpoints (human-in-the-loop)
- [x] CLI (parse, validate, transpile)
- [x] 121 tests (pytest)
- [x] PyPI package (`pip install epi-lang`)
- [ ] Template expansion for FastAPI target
- [ ] Academic paper (ArXiv submission)

## Related Work

| System | Relationship to Epi |
|--------|---------------------|
| [ProbZelus](https://dl.acm.org/doi/10.1145/3385412.3386009) (PLDI 2020) | Separates deterministic/probabilistic in reactive streams — Epi adapts this to full-stack transpilation |
| [SlicStan](https://dl.acm.org/doi/10.1145/3290348) (POPL 2019) | Information-flow types for probabilistic programs — Epi generalizes to application-level types |
| [BAML](https://github.com/BoundaryML/baml) | Typed LLM function signatures — Epi extends to full application generation |
| [Wasp](https://wasp-lang.dev) | Full-stack DSL (React + Node) — Epi adds epistemic types and AI-aware transpilation |

## Citation

If you use Epi in academic work, please cite:

```bibtex
@software{reboucas2026epi,
  author       = {Rebouças, Randerson},
  title        = {Epi: An Epistemic Programming Interface for AI-Aware Full-Stack Transpilation},
  year         = {2026},
  url          = {https://github.com/RandMelville/epi-lang},
  version      = {0.3.0}
}
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[Apache License 2.0](LICENSE) — Copyright (c) 2026 Randerson Rebouças
