# Epi — Epistemic Programming Interface

**A Zero-Stack Intent-Oriented Language with an Epistemic Type System.**

> *Research Status: Active / Structural Validation (v0.2)*
> *Author: Randerson Rebouças — UFRGS (PhD, Computing in Education)*

---

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

Over 60% of development time is spent on this infrastructure. Not on the idea. Not on the algorithm. On the *plumbing*.

Worse: when AI enters the picture, traditional type systems cannot distinguish between a value that was *computed* (a UUID) and a value that was *hallucinated* (an AI classification). A `string` is a `string`. The database doesn't know. The compiler doesn't care. And the hallucination becomes ground truth.

## The Solution

Epi is a language with **five primitives** and an **Epistemic Type System** that formally separates what is *known* (deterministic) from what must be *inferred* (stochastic) — in the same grammar, in the same file.

You write `.epi`. The transpiler generates a complete, auditable project: database schema, API routes, auth middleware, validation schemas, LLM inference functions, and UI components.

**One file in. Full stack out. Every AI output validated.**

## How It Looks

```epi
@Language: Epi v0.2
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

The transpiler generates **both** the inference call and its validation schema from the same declaration. If it compiles, it validates.

## Architecture

Three-layer transpiler. The LLM is only invoked in Layer 3.

```
.epi source → [Layer 1: Parser] → [Layer 2: Rigid Generator] → [Layer 3: Epistemic Generator]
               Lark + EBNF          Jinja2 templates              LLM (constrained)
               100% deterministic    100% deterministic             validated by Layer 2
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full technical breakdown.

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Parse and validate an .epi file
epi validate examples/contrato.epi

# Transpile to a full project
epi transpile examples/contrato.epi --target nextjs --outdir ./generated
```

## Project Structure

```
grammar/epi.lark          EBNF grammar
epi/parser/ast_nodes.py   Pydantic AST models
epi/parser/builder.py     Lark Transformer
epi/generators/           Code generators (deterministic + epistemic)
examples/contrato.epi     Canonical example
SPEC.md                   Formal language specification
ARCHITECTURE.md           Technical architecture
MANIFESTO.md              Project philosophy
```

## Documentation

| Document | Purpose |
|----------|---------|
| [SPEC.md](SPEC.md) | Formal language specification — grammar, type system, primitives |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Transpiler architecture — three layers, design decisions |
| [MANIFESTO.md](MANIFESTO.md) | Philosophy — why epistemic types matter |

## Status

**v0.2 — Research / Structural Validation**

- [x] Formal specification (SPEC.md)
- [x] EBNF grammar (Lark)
- [x] AST node models (Pydantic)
- [x] Lark Transformer (parser → AST)
- [x] Deterministic generators (Prisma, middleware, routes)
- [x] Epistemic generators (stubs)
- [x] CLI (parse, validate, transpile)
- [ ] End-to-end parser validation
- [ ] Template expansion for Next.js target
- [ ] Template expansion for FastAPI target
- [ ] Epistemic layer integration (Claude API)
- [ ] Lens → React component generation
- [ ] Academic paper (ArXiv preprint)

## License

MIT — Copyright (c) 2026 Randerson Rebouças
