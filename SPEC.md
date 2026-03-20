# Epi Language Specification v0.2

**Epi — Epistemic Programming Interface**
*A Zero-Stack Intent-Oriented Language with Epistemic Type System*

**Author:** Randerson Rebouças (UFRGS — Doutorado em Computação na Educação)
**Version:** 0.2
**Date:** 2026-03-19
**License:** MIT

---

## 1. Motivation

Large Language Models (LLMs) increasingly generate and consume source code. However, traditional programming languages (Python, JavaScript, SQL) present three fundamental problems for LLM-mediated development:

1. **High Entropy**: The same intent can be expressed in dozens of syntactically valid ways, increasing token consumption and hallucination probability.
2. **Forced Stack Separation**: Developers must maintain separate mental models for frontend, backend, database, and AI inference — each with its own language and conventions.
3. **No Epistemic Boundary**: There is no way to distinguish, within the same grammar, what is *known* (deterministic — e.g., a database schema) from what must be *inferred* (stochastic — e.g., an AI classification), leading to data corruption when LLMs hallucinate in rigid contexts.

Epi addresses all three by providing a **single grammar** with **five primitives** and an **Epistemic Type System** that formally separates deterministic and stochastic execution.

---

## 2. Core Concept: The Epistemic Type System

The central innovation of Epi is the **Epistemic Type System** — a type discipline that classifies every value in a program into one of two epistemic domains:

### 2.1 Rigid Types (Deterministic Domain)

Rigid types represent values that are fully determined at compile/transpile time. They map directly to database columns, API schemas, and static configuration.

```
UUID(auto)    → auto-generated unique identifier
Text          → string value
Int           → integer value
Float         → floating-point value
Decimal       → precise decimal (financial)
Bool          → boolean
DateTime(auto)→ timestamp, auto-populated
JSON          → arbitrary JSON structure
```

**Property**: A rigid type ALWAYS transpiles to the same output. No LLM involvement.

### 2.2 Epistemic Types (Stochastic Domain)

Epistemic types represent values that require AI inference but are **constrained** by formal validation schemas (Zod, Pydantic) generated at transpile time.

```
AI.Enum(Value1, Value2, ..., strict: true)  → AI infers, but must match enum
AI.Text(max_tokens: N)                       → AI generates text, length-bounded
AI.Classification(labels: [...])             → AI classifies into fixed labels
AI.Score(min: 0, max: 1)                     → AI scores within range
AI.Embedding(dimensions: N)                  → AI generates vector embedding
```

**Property**: An epistemic type generates BOTH the inference call AND the runtime validation schema. The AI may hallucinate — but the validation catches it.

### 2.3 The Epistemic Boundary

Within a single Entity, rigid and epistemic types coexist:

```epi
Entity Contrato {
    id: UUID(auto),              // Rigid — deterministic
    documento: Text,             // Rigid — deterministic
    risco: AI.Enum(Alto, Medio, Baixo, strict: true)  // Epistemic — AI-inferred, validated
}
```

The transpiler generates:
- **Prisma/SQLAlchemy schema** for rigid fields (template-based, no LLM)
- **Zod/Pydantic validator** for epistemic fields (template-based, no LLM)
- **LLM inference call** for epistemic field population (LLM-assisted, constrained)

---

## 3. The Five Primitives

### 3.1 Entity

Defines data schemas with epistemic type annotations.

**Syntax:**
```ebnf
entity ::= "Entity" IDENT "{" field ("," field)* "}"
field  ::= IDENT ":" type_expr
type_expr ::= rigid_type | epistemic_type
```

**Example:**
```epi
Entity Advogado {
    id: UUID(auto),
    nome: Text,
    oab: Text,
    especialidade: AI.Text(max_tokens: 50)
}
```

**Transpilation:**
- Rigid fields → database columns (Prisma model / SQLAlchemy model)
- Epistemic fields → database columns + runtime validation + AI inference function

---

### 3.2 Guard

Declares authentication and authorization constraints that transpile to middleware.

**Syntax:**
```ebnf
guard      ::= "Guard" IDENT "{" "Condition:" condition_expr "}"
condition  ::= dotted_name COMPARATOR literal
```

**Example:**
```epi
Guard SomenteAdvogados {
    Condition: Auth.Role == "Lawyer"
}
```

**Transpilation:**
- Next.js → middleware function checking `session.user.role`
- FastAPI → dependency function with `HTTPException(403)`

---

### 3.3 Pulse

The execution primitive — where logic occurs and hallucination is controlled. Every AI interaction is explicit, with mandatory parameters.

**Syntax:**
```ebnf
pulse      ::= "Pulse" IDENT "{" pulse_body "}"
pulse_body ::= "Input:" IDENT
               ("Protect:" dotted_name)?
               "Process:" process_step+
               ("Output:" type_or_ref)?
process_step ::= "Execute:" ai_call
ai_call    ::= "AI." FUNC "(" named_args ")"
```

**Mandatory AI call parameters:**
| Parameter | Purpose |
|-----------|---------|
| `source` | Input data reference |
| `prompt` | External prompt file via `file("@prompts/...")` |
| `temperature` | Controls randomness (lower = more deterministic) |
| `on_fail` | Fallback strategy when AI fails |

**Fallback Strategies:**
- `Fallback.ManualReview(Queue: "...")` — route to human queue
- `Fallback.ReturnEmpty` — return empty/null
- `Fallback.ReturnDefault(value: "...")` — return default value
- `Fallback.Retry(max: N)` — retry with backoff
- `Fallback.Escalate(to: "...")` — escalate to another system

**Example:**
```epi
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
```

**Key design decision**: By requiring `prompt: file(...)`, Epi forces prompts to be external, version-controlled files — not inline strings. This enables prompt auditing and A/B testing.

---

### 3.4 Pipeline

Composes Pulses into sequential business flows with error handling.

**Syntax:**
```ebnf
pipeline ::= "Pipeline" IDENT "{" "Flow:" IDENT ("->" IDENT)+ error_strategy? "}"
```

**Example:**
```epi
Pipeline AnalisarContrato {
    Flow: ExtrairRisco -> GerarResumo -> Notificar
    On_Error: Retry(max: 3, backoff: exponential)
}
```

**Transpilation:** Generates an API route that orchestrates the Pulse calls in sequence, with the declared error handling strategy.

---

### 3.5 Lens

Declares UI by semantic intent (Mood) with an escape hatch for native code injection.

**Syntax:**
```ebnf
lens    ::= "Lens" IDENT "{" lens_body "}"
lens_body ::= ("Mood:" STRING)? "Display:" display_items ("Inject:" STRING)?
```

**Widget types:** `Table`, `Form`, `Card`, `List`, `Chart`, `Button`, `Input`, `Modal`

**Example:**
```epi
Lens Dashboard {
    Mood: "Clean, Legal-Tech, Professional"
    Display:
        Table(Contrato, columns: [titulo, valor, risco]),
        Form(Contrato) -> Button("Analisar").trigger(ExtrairRisco)
    Inject: "<footer class='text-sm'>© 2026</footer>"
}
```

**Transpilation:**
- `Mood` → LLM generates styling/theme (epistemic layer)
- `Display` → component structure (deterministic templates)
- `Inject` → raw HTML/JSX passed through (escape hatch)

---

## 4. Transpiler Architecture

Epi uses a **three-layer transpiler** architecture:

```
    .epi source
        │
        ▼
┌───────────────────┐
│   Layer 1: Parser │  ← Lark (EBNF grammar)
│   (Deterministic) │     100% reproducible
└────────┬──────────┘
         │ AST (Pydantic models)
         ▼
┌───────────────────┐
│  Layer 2: Rigid   │  ← Jinja2 templates
│  Code Generator   │     Entity → Prisma
│  (Deterministic)  │     Guard → middleware
└────────┬──────────┘     Pipeline → routes
         │
         ▼
┌───────────────────┐
│ Layer 3: Epistemic│  ← LLM (Claude API)
│  Code Generator   │     AI.* types → inference code
│  (Constrained)    │     Lens.Mood → UI styling
└───────────────────┘
```

**Key property**: The LLM is ONLY invoked in Layer 3, and ONLY for AST nodes marked as epistemic (`AI.*`, `Mood`). The parser and rigid generator are fully deterministic.

---

## 5. File Extension

Epi source files use the `.epi` extension.

---

## 6. Complete Example

```epi
@Language: Epi v0.2
@Goal: "Análise de Contratos com Human-in-the-loop"

Entity Contrato {
    id: UUID(auto),
    titulo: Text,
    documento: Text,
    valor: Decimal,
    criado_em: DateTime(auto),
    risco: AI.Enum(Alto, Medio, Baixo, strict: true)
}

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
    Flow: ExtrairRisco -> Notificar
    On_Error: Retry(max: 3, backoff: exponential)
}

Lens Dashboard {
    Mood: "Clean, Legal-Tech"
    Display:
        Table(Contrato, columns: [titulo, valor, risco]),
        Form(Contrato) -> Button("Analisar").trigger(ExtrairRisco)
}
```

---

## 7. Related Work

| System | Relationship to Epi |
|--------|---------------------|
| **ProbZelus** (Baudart et al.) | Separates deterministic/probabilistic in reactive streams — Epi adapts this to full-stack transpilation |
| **SlicStan** (Gorinova et al.) | Information-flow type system for probabilistic programs — Epi generalizes to application-level types |
| **Gradual Typing** (Siek & Taha) | Mixes static/dynamic types via `?` — Epi's epistemic types add AI inference semantics |
| **BAML** (Boundary ML) | DSL for typed LLM function signatures — Epi extends to full application generation |
| **Wasp** (wasp-lang) | Full-stack DSL → React+Node — Epi adds epistemic types and multi-target transpilation |

---

## 8. License

MIT License — Copyright (c) 2026 Randerson Rebouças
