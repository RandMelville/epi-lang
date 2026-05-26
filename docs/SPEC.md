# Epi Language Specification v0.3

**Epi — Epistemic Programming Interface**
*A Zero-Stack Intent-Oriented Language with Epistemic Type System*

**Author:** Randerson Rebouças (UFRGS — Doutorado em Computação na Educação)
**Version:** 0.3
**Date:** 2026-03-25
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
AI.Score(min: 0, max: 1)                     → AI scores within range
AI.Embedding(dimensions: N)                  → AI generates vector embedding
```

**Property**: An epistemic type generates BOTH the inference call AND the runtime validation schema. The AI may hallucinate — but the validation catches it.

### 2.3 Distribution Prior (v0.3)

Epistemic Enum fields can declare a **Bayesian prior** — the initial probability distribution over values before any evidence is observed. This enables stochastic routing and Bayesian update generation.

```epi
avaliacao: AI.Enum(Correto, Parcial, Incorreto,
    prior: Distribution(Correto: 0.40, Parcial: 0.45, Incorreto: 0.15),
    confidence_threshold: 0.85
)
```

**Transpilation effects:**
- `prior` → generates `bayesianUpdate{Entity}{Field}()` TypeScript function implementing posterior ∝ likelihood × prior, normalized
- `confidence_threshold` → generates companion `{Schema}Confidence` Zod schema with `requiresReview: confidence < threshold`

**Two-level enforcement**: `confidence_threshold` on the Entity type is the *data layer* constraint (persisted validation). `on_low_confidence` inside an Execute call is the *runtime routing* constraint (triggers human review mid-pipeline). Both can coexist for defense-in-depth.

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

A Pulse has two execution modes:

**Classic mode** (`Process:`): single-step AI call, immediate output.

**Trace mode** (`Trace`): multi-step observable pipeline where each step is named, interruptible, and inspectable. Used when reasoning must be decomposed into auditable sub-tasks (e.g., `CompreenderEnunciado` → `AvaliarResposta`).

**Syntax:**
```ebnf
pulse      ::= "Pulse" IDENT "{" pulse_body "}"
pulse_body ::= "Input:" IDENT
               ("Protect:" dotted_name)?
               (pulse_process | pulse_traces)
               ("Output:" type_or_ref)?
pulse_process  ::= "Process:" ("Execute:" ai_call)+
pulse_traces   ::= trace+
trace          ::= "Trace" IDENT "{" trace_body "}"
trace_body     ::= "Execute:" ai_call
                   ("Expose:" IDENT ("," IDENT)*)?
                   ("Checkpoint:" checkpoint_strategy "(" args ")")?
ai_call        ::= "AI." FUNC "(" named_args ")"
```

**AI Functions:** `scan`, `classify`, `summarize`, `extract`, `generate`, `embed`, `reason`

The `reason` function signals chain-of-thought reasoning intent (same API call, different semantic annotation for tracing and audit purposes).

**Mandatory AI call parameters:**
| Parameter | Purpose |
|-----------|---------|
| `source` | Input data reference (e.g., `Input.documento`) |
| `prompt` | External prompt file via `file("@prompts/...")` |
| `temperature` | Controls randomness (lower = more deterministic) |
| `on_fail` | Fallback strategy when AI fails |

**Trace-specific parameters:**

| Construct | Purpose |
|-----------|---------|
| `Expose: field1, field2` | Fields in the AI's JSON output to make available to subsequent traces |
| `Checkpoint: ReviewRequired(...)` | Pause execution for human review before proceeding |
| `on_low_confidence: Checkpoint.ReviewRequired(...)` | Conditional pause — only triggers when `_confidence < threshold` |

**Fallback Strategies:**
- `Fallback.ManualReview(Queue: "...")` — route to human queue
- `Fallback.ReturnEmpty` — return empty/null
- `Fallback.ReturnDefault(value: "...")` — return default value
- `Fallback.Retry(max: N)` — retry with backoff
- `Fallback.Escalate(to: "...")` — escalate to another system

**Classic Pulse Example:**
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

### 3.3.1 Trace: Epistemic Debugging (v0.3)

Trace is the Epi mechanism for **epistemic debugging** — the ability to observe, interrupt, and validate intermediate reasoning steps inside a Pulse. This addresses a fundamental problem in AI-augmented systems: when a complex AI decision fails, there is no way to identify *which reasoning step* failed.

**Key properties of Trace:**

1. **Observable**: Each Trace step is named and its output is stored in a `TraceState` record, accessible via the generated `/inspect` API route.

2. **Interruptible**: A `Checkpoint` declaration pauses execution before the next step, storing the current state for human review. Execution resumes via the generated `/resume` route only after explicit human approval.

3. **Chainable**: The `Expose:` declaration makes specific fields from one Trace's AI output available as context for the next Trace.

**Checkpoint strategies:**
- `Checkpoint: ReviewRequired(...)` — unconditional pause (always requires human approval)
- `on_low_confidence: Checkpoint.ReviewRequired(...)` — conditional pause (triggers only when AI's `_confidence` field is below a threshold)

**The `_confidence` contract**: Prompts used in Trace steps must include a `_confidence` field (0.0–1.0) in their JSON output. This is enforced by convention (documented in the prompt file) and extracted at runtime by the generated Trace execution code.

**Generated infrastructure for a Trace Pulse:**
- `lib/trace-store.ts` — in-memory store for `TraceState` (keyed by traceId, includes `originalInput`, step outputs, and `pipelineStatus`)
- `traces/{pulse}/{trace}.ts` — execution function for each Trace step (calls Claude, extracts `_confidence`, saves state, checks `shouldPause`)
- `app/api/traces/{pulse}/[traceId]/inspect/route.ts` — GET route for human review UI
- `app/api/traces/{pulse}/[traceId]/resume/route.ts` — POST route to accept a step output and chain to the next Trace

**Trace Pulse Example:**
```epi
Pulse AvaliarRespostaAluno {
    Input: Submissao

    Trace CompreenderEnunciado {
        Execute: AI.reason(
            source: Input.enunciado,
            prompt: file("@prompts/compreender-enunciado.md"),
            temperature: 0.2,
            on_fail: Fallback.ReturnEmpty
        )
        Expose: interpretacao, conceitos_chave, criterios_avaliacao
        Checkpoint: ReviewRequired()
    }

    Trace AvaliarResposta {
        Execute: AI.classify(
            source: Input.resposta,
            prompt: file("@prompts/avaliar-pedagogicamente.md"),
            temperature: 0.1,
            on_fail: Fallback.ManualReview(Queue: "Professores"),
            on_low_confidence: Checkpoint.ReviewRequired()
        )
    }
}
```

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

### 6.1 Classic Pulse (Legal Analysis)

```epi
@Language: Epi v0.3
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

### 6.2 Trace Pulse with Stochastic Routing (EdTech)

This example demonstrates v0.3 features: Trace, Checkpoint, Distribution prior, and confidence_threshold.

```epi
@Language: Epi v0.3
@Goal: "Avaliação pedagógica com raciocínio epistêmico observável"

Entity Aluno {
    id: UUID(auto),
    nome: Text
}

Entity Submissao {
    id: UUID(auto),
    enunciado: Text,
    resposta: Text,
    avaliacao: AI.Enum(Correto, Parcial, Incorreto,
        prior: Distribution(Correto: 0.40, Parcial: 0.45, Incorreto: 0.15),
        confidence_threshold: 0.85
    ),
    justificativa: AI.Text(max_tokens: 200),
    aluno_id: Text
}

Guard SomenteProfessores {
    Condition: Auth.Role == "Teacher"
}

Pulse AvaliarRespostaAluno {
    Input: Submissao

    Trace CompreenderEnunciado {
        Execute: AI.reason(
            source: Input.enunciado,
            prompt: file("@prompts/compreender-enunciado.md"),
            temperature: 0.2,
            on_fail: Fallback.ReturnEmpty
        )
        Expose: interpretacao, conceitos_chave, criterios_avaliacao
        Checkpoint: ReviewRequired()
    }

    Trace AvaliarResposta {
        Execute: AI.classify(
            source: Input.resposta,
            prompt: file("@prompts/avaliar-pedagogicamente.md"),
            temperature: 0.1,
            on_fail: Fallback.ManualReview(Queue: "Professores"),
            on_low_confidence: Checkpoint.ReviewRequired()
        )
    }
}

Pipeline AvaliacaoPedagogica {
    Flow: AvaliarRespostaAluno
    On_Error: Retry(max: 2, backoff: fixed)
}
```

**Generated artifacts for this program:**
- `prisma/schema.prisma` — Aluno + Submissao models
- `validators/submissao.ts` — Zod schemas for `avaliacao` and `justificativa`
- `validators/submissao.ts` — `bayesianUpdateSubmissaoAvaliacao()` function (from `prior:`)
- `validators/submissao.ts` — `SubmissaoAvaliacaoSchemaConfidence` schema (from `confidence_threshold:`)
- `lib/trace-store.ts` — TraceState store
- `traces/avaliar-resposta-aluno/compreender-enunciado.ts` — Trace 1 executor
- `traces/avaliar-resposta-aluno/avaliar-resposta.ts` — Trace 2 executor
- `app/api/traces/avaliar-resposta-aluno/[traceId]/inspect/route.ts`
- `app/api/traces/avaliar-resposta-aluno/[traceId]/resume/route.ts`

---

## 7. Related Work

Epi draws on and distinguishes itself from four lineages of prior work: (a) probabilistic programming languages, (b) gradual type systems, (c) LLM-oriented DSLs, and (d) full-stack code generation tools. The table below additionally includes classical languages that address adjacent concerns — symbolic AI (Lisp, Prolog), statistical computing (R), and high-performance scientific computation (Julia) — to clarify Epi's architectural boundaries.

| System | Relationship to Epi |
|--------|---------------------|
| **ProbZelus** (Baudart et al., PLDI 2020) | Separates deterministic/probabilistic execution in reactive streams — Epi adapts this separation to full-stack application transpilation |
| **SlicStan** (Gorinova et al., POPL 2019) | Information-flow type system for probabilistic programs — Epi generalizes information-flow separation to application-level types (database vs. AI-inferred) |
| **Gradual Typing** (Siek & Taha, 2006) | Mixes static/dynamic types via the `?` type — Epi's Rigid/Epistemic boundary is structurally analogous, but replaces the static–dynamic axis with a deterministic–stochastic axis, adding AI inference semantics and mandatory runtime validation |
| **BAML** (Boundary ML) | DSL for typed LLM function signatures — Epi extends beyond function-level typing to full application generation (database, routes, UI) from a single declaration |
| **Wasp** (wasp-lang) | Full-stack DSL generating React + Node.js — Epi adds the Epistemic Type System and AI-aware transpilation; Wasp has no mechanism for distinguishing deterministic from AI-inferred values |
| **Lisp** (McCarthy, 1960) | Pioneer of symbolic AI and homoiconicity — Epi shares the philosophy of minimal primitives (Lisp's 7 forms, Epi's 5 primitives) but operates at the application orchestration layer rather than the symbolic computation layer; Epi does not implement symbolic evaluation or macro expansion |
| **Prolog** (Colmerauer & Roussel, 1972) | Logic programming via Horn clauses and unification — Epi's Guard primitive echoes Prolog's declarative constraints, but Epi delegates inference to external LLMs rather than implementing its own resolution engine; Epi's scope is application generation, not automated theorem proving |
| **R** (Ihaka & Gentleman, 1996) | Domain-specific language for statistical computing — R operates at the data analysis and model-fitting layer; Epi operates at the application orchestration layer and delegates statistical computation to AI model endpoints via Pulse |
| **Julia** (Bezanson et al., 2017) | High-performance scientific computing with multiple dispatch — Julia targets the model computation layer (tensor operations, automatic differentiation, GPU kernels); Epi targets the application orchestration layer and would invoke Julia-built models as external services via Pulse |

---

## 8. Ethics by Design and Explainability

Epi incorporates ethical safeguards and decision explainability as structural properties of the language, not as optional libraries or conventions. This approach is informed by Pereira's proposal for programming ethics into AI systems (Pereira, 2020; Pereira & Saptawijaya, 2016), which argues that ethical constraints must be *computationally enforceable* — embedded in the execution model itself, not delegated to post-hoc auditing.

### 8.1 Structural Ethical Safeguards

Epi enforces ethical constraints through four mechanisms that are mandatory elements of the grammar, not optional annotations:

| Mechanism | Grammar Element | Ethical Property |
|-----------|----------------|------------------|
| **Mandatory fallback** | `on_fail` parameter in every `AI.*` call | No AI decision can silently fail. Every inference path has an explicit degradation strategy, including `ManualReview` for human-in-the-loop oversight |
| **External prompt auditing** | `file("@prompts/...")` syntax | Prompts are version-controlled artifacts, not inline strings. Every prompt can be audited, diffed, reviewed, and A/B tested — creating a complete decision audit trail |
| **Guard-enforced authorization** | `Guard` primitive with `Protect:` reference | AI-driven operations are subject to the same authorization constraints as deterministic operations. The transpiler rejects a Pulse that references a nonexistent Guard |
| **Epistemic validation boundary** | `AI.*` types → Zod/Pydantic schemas | AI outputs are structurally validated before persistence. A hallucinated value outside the declared enum/range/schema is rejected at runtime, preventing bias propagation into the database |

### 8.2 Explainability Properties

Every AI decision made through Epi is explainable by construction:

1. **Traceability**: Each AI inference is traceable to a specific Pulse, which declares its input Entity, prompt file, temperature, and fallback strategy. There are no implicit AI calls.

2. **Reproducibility**: The `temperature` parameter is mandatory and explicit. Combined with the external prompt file and the declared input source, a third party can reproduce the conditions under which any AI decision was made.

3. **Auditability**: The three-layer transpiler architecture guarantees that all deterministic code (database schemas, API routes, middleware) is generated without LLM involvement. Only Layer 3 (Epistemic) involves AI, and its outputs are constrained by Layer 2 validators. An auditor need only inspect Layer 3 outputs and the prompt files to understand all AI-influenced behavior.

4. **Human override**: The `Fallback.ManualReview(Queue: "...")` strategy explicitly routes uncertain decisions to human reviewers, implementing the human-in-the-loop pattern as a first-class language construct rather than an application-level workaround.

### 8.3 References

- Pereira, L. M. (2020). *Programming Machine Ethics*. Springer.
- Pereira, L. M., & Saptawijaya, A. (2016). *Programming Machine Ethics*. Studies in Applied Philosophy, Epistemology and Rational Ethics, vol 26. Springer, Cham.
- Floridi, L., & Cowls, J. (2019). A unified framework of five principles for AI in society. *Harvard Data Science Review*, 1(1).

---

## 9. Scope Boundary: Orchestration vs. Computation

Epi is an **application orchestration language**. It declares *what* an AI-augmented application should do and delegates *how* to specialized engines. This section formally defines the boundary between what Epi handles and what it delegates.

### 9.1 What Epi Handles

| Concern | Mechanism | Layer |
|---------|-----------|-------|
| Data schema definition | Entity → Prisma/SQLAlchemy | Layer 2 (Deterministic) |
| Authentication and authorization | Guard → middleware | Layer 2 (Deterministic) |
| AI inference orchestration | Pulse → LLM API call with validation | Layer 3 (Epistemic) |
| Business flow composition | Pipeline → route with error handling | Layer 2 (Deterministic) |
| UI declaration by intent | Lens → component scaffold + AI styling | Layers 2+3 |
| Runtime validation of AI outputs | Epistemic types → Zod/Pydantic schemas | Layer 2 (Deterministic) |
| Decision audit trail | External prompts + fallback strategies | Grammar-enforced |

### 9.2 What Epi Delegates

| Concern | Delegated To | Rationale |
|---------|-------------|-----------|
| Tensor operations, linear algebra | PyTorch, TensorFlow, JAX | Epi operates above the model computation layer. A Pulse invokes a model endpoint; it does not implement the model |
| Automatic differentiation | Autograd libraries (PyTorch, JAX) | Differentiation is a property of the computation graph, not the orchestration graph |
| GPU/TPU kernel optimization | CUDA, XLA, Metal via ML frameworks | Hardware-level optimization is orthogonal to application-level intent declaration |
| Model training and fine-tuning | ML pipelines (MLflow, Kubeflow, W&B) | Training produces models; Epi consumes models. The lifecycle boundary is at the model API endpoint |
| Statistical computation | R, Julia, Python (scipy, statsmodels) | Statistical analysis is a computational concern; Epi orchestrates the results of computation |
| Symbolic reasoning and unification | Prolog, Datalog, knowledge graph engines | Epi's Guard primitive handles declarative constraints for authorization; full symbolic reasoning is delegated to specialized engines |
| Low-level parallelism and threading | Target language runtime (Node.js event loop, Python asyncio) | Epi's Pipeline declares sequential composition; the transpiler generates appropriate concurrency primitives in the target |

### 9.3 The Composition Principle

Epi's scope boundary follows the **composition principle**: the language achieves maximum expressiveness not by incorporating every computational paradigm, but by composing cleanly with specialized tools at well-defined interfaces.

A concrete example: a developer building a contract analysis system with a custom NLP model would:

1. **Train the model** in PyTorch/JAX (outside Epi)
2. **Deploy it** as an API endpoint (e.g., FastAPI + Docker)
3. **Invoke it from Epi** via a Pulse with the endpoint as the AI provider
4. **Validate its output** via the Epistemic Type System (inside Epi)

This is analogous to SQL declaring `SELECT * FROM contracts WHERE risk = 'high'` without specifying the B-tree traversal algorithm. The power is in the declaration, not the computation.

> *"The expressive power of a language is determined not only by what it can express, but by what it can safely exclude."*
> — cf. Felleisen, M. (1991). "On the Expressive Power of Programming Languages." *Science of Computer Programming*, 17(1-3), pp. 35–75.

---

## 10. License

Apache License 2.0 — Copyright (c) 2026 Randerson Rebouças
