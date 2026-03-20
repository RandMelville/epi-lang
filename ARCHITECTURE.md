# Epi Architecture

**Three-Layer Epistemic Transpiler**

*Version 0.2 — March 2026*

---

## Overview

Epi's transpiler is organized into three formally separated layers. The critical design invariant is: **the LLM is never invoked in Layers 1 or 2.** Only Layer 3 (Epistemic) involves non-deterministic computation, and even there, every output is constrained by validation schemas generated deterministically in Layer 2.

```
                   ┌─────────────────────────┐
                   │      .epi source file    │
                   │   (Entity, Guard, Pulse, │
                   │    Pipeline, Lens)        │
                   └────────────┬────────────┘
                                │
                   ┌────────────▼────────────┐
                   │   LAYER 1: SYNTACTIC     │
                   │   Parser (Lark + EBNF)   │
                   │   ● 100% deterministic   │
                   │   ● .epi → AST           │
                   └────────────┬────────────┘
                                │ Pydantic AST models
                   ┌────────────▼────────────┐
                   │   LAYER 2: DETERMINISTIC │
                   │   Rigid Code Generator   │
                   │   ● Jinja2 templates     │
                   │   ● Entity → Prisma/SQL  │
                   │   ● Guard → middleware    │
                   │   ● Pipeline → routes    │
                   │   ● AI.* → validators    │
                   └────────────┬────────────┘
                                │ Generated project scaffold
                   ┌────────────▼────────────┐
                   │   LAYER 3: EPISTEMIC     │
                   │   AI Code Generator      │
                   │   ● LLM inference stubs  │
                   │   ● Lens.Mood → styling  │
                   │   ● Constrained by L2    │
                   │     validation schemas   │
                   └─────────────────────────┘
```

---

## Layer 1 — Syntactic (Parser)

**Input:** `.epi` source file
**Output:** Typed AST (Pydantic models)
**Determinism:** 100% — no LLM, no network, no side effects

### Grammar

The Epi grammar is defined in EBNF notation and processed by [Lark](https://github.com/lark-parser/lark), a Python parsing library that supports Earley and LALR(1) parsing.

```
grammar/epi.lark     → EBNF grammar definition
epi/parser/builder.py → Lark Transformer that converts parse tree → typed AST
epi/parser/ast_nodes.py → Pydantic models for all AST node types
```

### Parse Flow

```
.epi source
    │
    ▼
Lark(grammar="epi.lark", parser="earley")
    │
    ▼
Lark Parse Tree (untyped)
    │
    ▼
EpiTransformer(lark.Transformer)
    │  ─ Visits each node
    │  ─ Constructs Pydantic models
    │  ─ Validates types at construction time
    ▼
EpiProgram (typed AST root)
    ├── metadata: list[Metadata]
    ├── entities: list[Entity]
    ├── guards: list[Guard]
    ├── pulses: list[Pulse]
    ├── pipelines: list[Pipeline]
    └── lenses: list[Lens]
```

### Why Lark

| Criterion | Lark | ANTLR | Tree-sitter |
|-----------|------|-------|-------------|
| Python-native | Yes | Java-first | C-first |
| EBNF syntax | Native | Extended | JSON-based |
| Earley support | Yes | No | No |
| Install complexity | `pip install lark` | JRE + codegen | C compiler |
| Ambiguity handling | Earley resolves | Error | Error |

Lark's Earley parser tolerates grammar ambiguity during rapid iteration — essential for a research-stage language. Migration to LALR(1) is a future optimization once the grammar stabilizes.

### AST Nodes

Every AST node is a Pydantic `BaseModel`, providing:

- **Type validation at construction** — malformed ASTs are caught immediately
- **Serialization** — AST can be dumped to JSON for debugging and testing
- **Immutability** — `model_config = ConfigDict(frozen=True)` prevents mutation after construction

Key node types:

| Node | Fields | Represents |
|------|--------|------------|
| `Entity` | name, fields[] | Data schema with epistemic annotations |
| `Field` | name, type_expr | Single field (rigid or epistemic) |
| `RigidType` | base, modifiers | Deterministic type (UUID, Text, etc.) |
| `EpistemicType` | kind, args | AI-inferred type (AI.Enum, AI.Text, etc.) |
| `Guard` | name, condition | Auth/authorization constraint |
| `Pulse` | name, input, protect?, process, output? | AI execution unit |
| `Pipeline` | name, flow[], error_strategy? | Pulse composition |
| `Lens` | name, mood?, display[], inject? | UI declaration |

---

## Layer 2 — Deterministic (Rigid Code Generator)

**Input:** Typed AST from Layer 1
**Output:** Complete project scaffold (database, API, middleware, validators)
**Determinism:** 100% — Jinja2 templates, no LLM

### Generation Targets

Layer 2 reads the AST and generates code using Jinja2 templates. Each AST node type maps to a specific generator:

```
epi/generators/deterministic/
    ├── prisma.py      → Entity → Prisma schema / SQLAlchemy models
    ├── middleware.py   → Guard → auth middleware functions
    └── routes.py      → Pipeline → API route orchestration
```

### Entity → Database Schema

For each `Entity`, the generator:

1. **Extracts rigid fields** → generates database columns
2. **Extracts epistemic fields** → generates database columns (for storage) + Zod/Pydantic validation schemas (for runtime constraint)

```
Entity Contrato {                    model Contrato {
    id: UUID(auto),          →           id    String @id @default(uuid())
    titulo: Text,            →           titulo String
    risco: AI.Enum(...)      →           risco  String   // stored as string
}                                    }

                                     // + generated validator:
                                     const ContratoRiscoSchema = z.enum(["Alto", "Medio", "Baixo"])
```

The epistemic field `risco` gets **both** a database column (rigid storage) and a validation schema (epistemic constraint). This is the Epistemic Boundary in action: the database doesn't know the value was AI-generated, but the application layer enforces that only valid inferences are persisted.

### Guard → Middleware

Each `Guard` generates a middleware function:

```
Guard SomenteAdvogados {             export function guardSomenteAdvogados(session) {
    Condition: Auth.Role == "Lawyer"     if (session.user.role !== "Lawyer") {
}                                →           throw new ForbiddenError("...")
                                         }
                                     }
```

### Pipeline → API Routes

Each `Pipeline` generates an API endpoint that orchestrates its `Flow` sequence:

```
Pipeline AnalisarContrato {          POST /api/analisar-contrato
    Flow: A -> B -> C        →       1. await pulseA(input)
    On_Error: Retry(max: 3)          2. await pulseB(result)
}                                    3. await pulseC(result)
                                     catch: retry with backoff (max 3)
```

---

## Layer 3 — Epistemic (AI Code Generator)

**Input:** AST nodes marked as epistemic (`AI.*` types, `Lens.Mood`)
**Output:** LLM inference functions + UI theme/styling
**Determinism:** Constrained non-deterministic — outputs validated by Layer 2 schemas

### AI Function Generation

For each `Pulse` containing `AI.*` calls, Layer 3 generates:

1. **Inference function** — calls the LLM with the declared prompt, temperature, and source
2. **Validation wrapper** — applies the Zod/Pydantic schema from Layer 2
3. **Fallback handler** — implements the declared `on_fail` strategy

```python
# Generated from: Pulse ExtrairRisco
async def pulse_extrair_risco(contrato: Contrato) -> str:
    raw = await llm.invoke(
        prompt=load_prompt("@prompts/legal_scan.md"),
        source=contrato.documento,
        temperature=0.1,
    )

    # Layer 2 validator constrains Layer 3 output
    validated = ContratoRiscoSchema.parse(raw)

    if validated is None:
        return await fallback_manual_review(queue="Advogados")

    return validated
```

### Lens Mood Generation

The `Mood` field in a `Lens` is the one place where the LLM has creative freedom — but only for styling, never for structure:

| Generated by | Source | Deterministic? |
|--------------|--------|----------------|
| Component structure | `Display:` declarations | Yes — templates |
| Data bindings | Entity references | Yes — templates |
| Theme/styling | `Mood:` string | No — LLM-generated |
| Escape hatch | `Inject:` raw HTML | Yes — passthrough |

### The Constraint Chain

The safety of Layer 3 depends on a formal constraint chain:

```
.epi declaration
    │
    ├─ Layer 2 generates: validation schema (Zod/Pydantic)
    │
    └─ Layer 3 generates: LLM inference call
                              │
                              ▼
                         LLM raw output
                              │
                              ▼
                     Layer 2 validator ──── PASS → store in DB
                              │
                              └──── FAIL → on_fail strategy
```

The developer never writes the validator manually. The transpiler guarantees that every epistemic type has a corresponding validator. **If it compiles, it validates.**

---

## Directory Structure

```
epi/
├── grammar/
│   └── epi.lark                    # EBNF grammar (Layer 1 input)
├── epi/
│   ├── cli.py                      # Typer CLI: parse, validate, transpile
│   ├── parser/
│   │   ├── ast_nodes.py            # Pydantic AST models
│   │   └── builder.py              # Lark Transformer
│   └── generators/
│       ├── deterministic/          # Layer 2
│       │   ├── prisma.py           # Entity → Prisma schema
│       │   ├── middleware.py       # Guard → auth middleware
│       │   └── routes.py           # Pipeline → API routes
│       └── epistemic/              # Layer 3
│           ├── ai_scan.py          # AI.* → inference functions
│           └── lens_mood.py        # Mood → LLM styling
├── examples/
│   └── contrato.epi                # Canonical example
├── tests/                          # pytest suite
├── SPEC.md                         # Formal language specification
├── MANIFESTO.md                    # Project philosophy
├── ARCHITECTURE.md                 # This document
├── pyproject.toml                  # Build configuration
└── README.md                       # Project entry point
```

---

## Design Decisions Log

| Decision | Rationale | Alternative considered |
|----------|-----------|----------------------|
| Lark over ANTLR | Python-native, Earley support, zero external deps | ANTLR requires JRE, adds build complexity |
| Pydantic for AST | Validation + serialization + immutability in one library | dataclasses (no validation), attrs (no JSON) |
| Jinja2 for templates | Industry standard, logic-free, well-documented | Mako (too powerful), string formatting (unmaintainable) |
| Earley over LALR | Tolerates ambiguity during grammar iteration | LALR is faster but rejects ambiguous grammars |
| External prompts (`file()`) | Version control, auditing, A/B testing | Inline strings (untraceable, untestable) |
| Validation at epistemic boundary | Single point of trust, generated from types | Manual validation (error-prone, inconsistent) |

---

*This architecture is designed to evolve. Layer 1 (grammar) will stabilize first. Layer 2 (templates) will expand to support multiple targets. Layer 3 (epistemic) will deepen as LLM capabilities grow. The invariant — that LLMs never touch deterministic code — will not change.*
