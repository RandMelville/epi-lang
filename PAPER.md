# Epistemic Type Systems: Unifying Deterministic and Stochastic Execution in a Single Grammar

**Randerson Rebouças**
Programa de Pós-Graduação em Informática na Educação, UFRGS
randerson@inf.ufrgs.br

**Preprint — submitted to arXiv cs.PL / cs.AI**
*March 2026*

---

## Abstract

We introduce **Epi** (*Epistemic Programming Interface*), a domain-specific language and transpiler that addresses a fundamental gap in AI-augmented software development: the absence of a type discipline that formally distinguishes *deterministic* values (database schemas, business rules) from *stochastic* values (LLM-inferred classifications, AI-generated text) within a single grammar. Epi's **Epistemic Type System** classifies every field in a program as either *Rigid* (deterministic, maps to a database column and a template-generated schema) or *Epistemic* (AI-inferred, constrained at runtime by generated Zod/Pydantic validators). From a single `.epi` source file, the Epi transpiler generates a complete, runnable Next.js or FastAPI project — including database schema, authentication middleware, AI inference functions, runtime validators, and UI scaffolding. We describe the language design, transpiler architecture, two real-world case studies (legal contract analysis and pedagogical assessment), and a test suite of 121 unit tests. The language is available as open-source software at https://github.com/RandMelville/epi-lang.

---

## 1. Introduction

Large Language Models (LLMs) are increasingly integrated into production software systems — performing classification, extraction, summarization, and generation. Yet the dominant programming languages (Python, JavaScript, TypeScript) were designed in an era when all computation was deterministic: a function given the same input reliably produces the same output. This assumption fails catastrophically when LLMs are involved.

Three concrete problems arise when building LLM-augmented applications with conventional languages:

**Problem 1 — No type-level separation of epistemic domains.** A database schema field `status VARCHAR` and an LLM-inferred field `risk AI.Enum(High, Medium, Low)` are treated identically by the type system. If the LLM hallucinates `"Unknown"` for `risk`, the value propagates silently into the database. There is no compile-time or type-system mechanism to require runtime validation of AI-inferred values.

**Problem 2 — Forced stack fragmentation.** Building an AI-augmented application requires maintaining separate mental models, languages, and toolchains for: (a) the database schema (SQL/Prisma), (b) the API layer (TypeScript/Python), (c) the frontend (React/JSX), and (d) the AI inference layer (Anthropic SDK, LangChain). A developer must hold four grammars simultaneously.

**Problem 3 — No grammar-enforced hallucination contract.** LLM calls in conventional code are unconstrained: any string can be returned, any JSON structure accepted. Fallback strategies, prompt management, temperature control, and output validation are all optional — and frequently omitted.

Epi addresses all three problems by providing a **single grammar** with **five primitives**, an **Epistemic Type System**, and a **three-layer transpiler** that generates deterministic and stochastic code from a common declaration.

The contribution of this paper is:
1. The definition of the **Epistemic Type System** — a type discipline that unifies deterministic and stochastic execution in a single grammar.
2. The **Epi language design** — five minimal primitives (Entity, Guard, Pulse, Pipeline, Lens) and their formal grammar.
3. The **Epi transpiler** — a three-layer architecture (Parse → Rigid Generator → Epistemic Generator) that produces complete, runnable projects.
4. An **evaluation** on two domain case studies and a 121-test suite.

---

## 2. Background and Motivation

### 2.1 Type Systems and Safety

Type systems have long been the primary mechanism for ruling out classes of program errors at compile time [PIERCE]. Gradual typing [SIEK2006] extends this to allow mixing of typed and untyped code via the dynamic type `?`. Epi's Rigid/Epistemic boundary is structurally analogous: it permits coexistence of deterministic and stochastic values in a single program, while requiring that the epistemic values be validated at the boundary before they can be persisted.

The key difference is semantic: where gradual typing's `?` defers *static* type checking to runtime, Epi's `AI.*` types generate both the *inference call* and the *runtime validation schema*. The transpiler ensures that epistemic values cannot bypass validation.

### 2.2 Probabilistic Programming

Probabilistic programming languages (PPLs) such as ProbZelus [BAUDART2020] and Stan [STAN2017] address stochastic computation by embedding probability distributions as first-class language constructs. Epi draws inspiration from this lineage — particularly ProbZelus's separation of deterministic reactive streams from probabilistic streams — but operates at a different layer: application orchestration rather than model computation. Epi invokes pre-trained AI model endpoints; it does not implement inference algorithms.

SlicStan [GORINOVA2019] introduces an information-flow type system for Stan programs, separating data, transformed parameters, and model components. Epi's Rigid/Epistemic separation is analogous at the application layer: rigid types represent data known at schema definition time, epistemic types represent values that flow through AI inference at runtime.

### 2.3 LLM-Oriented DSLs and Full-Stack Generators

**BAML** (Boundary ML) provides typed function signatures for LLM calls, generating type-safe wrappers with Pydantic/Zod validation. Epi extends this approach from function-level typing to full application generation, with the Epistemic Type System integrated into the database schema and UI declaration.

**Wasp** [WASP2022] is a declarative DSL generating React + Node.js applications. Epi is architecturally similar but adds AI-aware transpilation: Wasp has no mechanism for distinguishing deterministic from AI-inferred values, and no hallucination control primitives.

**Wing** [WING2024] provides cloud-oriented programming with compile-time infrastructure targeting. Epi shares Wing's philosophy of single-source-of-truth for full-stack concerns but focuses on the AI inference layer rather than cloud infrastructure.

---

## 3. The Epi Language

Epi programs consist of five primitive declarations: **Entity**, **Guard**, **Pulse**, **Pipeline**, and **Lens**. Together, they express the complete data, security, logic, composition, and UI concerns of an AI-augmented application.

### 3.1 Syntax Overview

```ebnf
program    ::= metadata* primitive*
primitive  ::= entity | guard | pulse | pipeline | lens
metadata   ::= "@" IDENT ":" STRING
entity     ::= "Entity" IDENT "{" field ("," field)* "}"
field      ::= IDENT ":" type_expr
type_expr  ::= rigid_type | epistemic_type
rigid_type ::= "UUID" | "Text" | "Int" | "Float" | "Decimal"
             | "Bool" | "DateTime" | "JSON"
             | rigid_type "(" named_args ")"
epistemic_type ::= "AI." FUNC "(" named_args ")"
FUNC       ::= "Enum" | "Text" | "Score" | "Embedding"
```

### 3.2 Entity — Data Schema with Epistemic Annotations

An Entity defines a data schema in which fields may be either Rigid (deterministic) or Epistemic (AI-inferred):

```epi
Entity Contrato {
    id: UUID(auto),
    documento: Text,
    valor: Decimal,
    risco: AI.Enum(Alto, Medio, Baixo, strict: true)
}
```

**Transpilation effect:** The Epi transpiler generates (a) a Prisma model for all fields, mapping rigid types to SQL columns and epistemic types to `String` columns with a DB-level enum constraint; (b) a Zod schema for each epistemic field, enforcing the declared constraint at runtime.

**Distribution Prior (v0.3):** Epistemic Enum fields can declare a Bayesian prior distribution over their values. The transpiler generates a `bayesianUpdate()` TypeScript function implementing posterior ∝ likelihood × prior:

```epi
avaliacao: AI.Enum(Correto, Parcial, Incorreto,
    prior: Distribution(Correto: 0.40, Parcial: 0.45, Incorreto: 0.15),
    confidence_threshold: 0.85
)
```

### 3.3 Guard — Authorization as First-Class Primitive

Guards declare authentication and authorization constraints that transpile to middleware. The `Protect:` keyword in a Pulse enforces that the Guard is checked before AI inference begins:

```epi
Guard SomenteAdvogados {
    Condition: Auth.Role == "Lawyer"
}
```

By making authorization a grammar-level primitive rather than a library call, Epi ensures that AI-driven operations are subject to the same access control as deterministic operations. The transpiler rejects a Pulse that references a nonexistent Guard.

### 3.4 Pulse — Logic and Hallucination Control

The Pulse primitive is where AI inference occurs. Every AI call within a Pulse is explicit and requires mandatory parameters: `source` (input data reference), `prompt` (external file path), `temperature`, and `on_fail` (fallback strategy):

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

**The mandatory prompt file pattern** (`file("@prompts/...")`) is a deliberate design decision: prompts are version-controlled artifacts, not inline strings. This creates a complete audit trail — every AI decision can be traced to a specific, diff-able prompt file.

**Fallback strategies** are grammar-enforced: `ManualReview`, `ReturnEmpty`, `ReturnDefault`, `Retry`, and `Escalate`. There is no `on_fail`-less AI call in valid Epi syntax.

**Trace mode (v0.3):** For multi-step reasoning, Pulses can declare named, observable Trace steps with explicit `Expose:` (output fields for subsequent steps) and `Checkpoint:` (unconditional or confidence-conditional pause for human review):

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

### 3.5 Pipeline — Sequential Composition with Error Handling

Pipelines compose Pulses into sequential flows. Error strategies (`Retry`, `Halt`, `Fallback`) are declared at the composition level, not within individual Pulses:

```epi
Pipeline AnalisarContrato {
    Flow: ExtrairRisco -> GerarResumo -> Notificar
    On_Error: Retry(max: 3, backoff: exponential)
}
```

### 3.6 Lens — Semantic UI Declaration

The Lens primitive declares UI by semantic intent (`Mood`) rather than by component specification. A `Mood` is a natural language string that describes the desired aesthetic and is processed by the Epistemic Layer of the transpiler:

```epi
Lens Dashboard {
    Mood: "Clean, Legal-Tech, Professional"
    Display:
        Table(Contrato, columns: [titulo, valor, risco]),
        Form(Contrato) -> Button("Analisar").trigger(ExtrairRisco)
    Inject: "<footer class='text-sm'>© 2026</footer>"
}
```

The `Inject` escape hatch allows raw HTML/JSX passthrough for elements that resist semantic declaration.

---

## 4. The Epistemic Type System

The Epistemic Type System is the central contribution of Epi. It partitions every value in a program into one of two epistemic domains:

**Definition 1 (Rigid Type).** A type *T* is *rigid* if its value is fully determined at compile/transpile time and maps directly to a database column through a deterministic schema. No LLM is involved in the generation or validation of rigid values.

**Definition 2 (Epistemic Type).** A type *T* is *epistemic* if its value requires AI inference at runtime. The transpiler generates both the inference call and a runtime validation schema (Zod for TypeScript, Pydantic for Python) from the type declaration alone.

**Definition 3 (Epistemic Boundary).** Within a single Entity, rigid and epistemic types coexist. The epistemic boundary is the interface at which AI-inferred values are validated before being persisted alongside rigid values.

The key formal property is:

**Theorem 1 (Validation Completeness).** For every epistemic field *f* of type `AI.T(args)` in any Entity *E*, the transpiler generates a validator *V(f)* such that every value assigned to *f* at runtime is checked against *V(f)* before persistence. A validation failure triggers the declared `on_fail` strategy.

*Proof sketch:* By construction in the transpiler's Rigid Code Generator (Layer 2): `generate_validators()` iterates over all entities and their epistemic fields, emitting one Zod/Pydantic schema per field. The generated Pulse code (Layer 3) imports and applies these validators to all AI call results. □

**Corollary 1 (Hallucination Containment).** An LLM hallucination that produces a value outside the declared epistemic type's constraint will be caught by the generated validator and will not reach the database.

### 4.1 Rigid Type Constructors

| Constructor | Semantic | DB Column |
|-------------|----------|-----------|
| `UUID(auto)` | Auto-generated UUID | `@id @default(uuid())` |
| `Text` | Unbounded string | `String` |
| `Int` | Integer | `Int` |
| `Float` | Floating-point | `Float` |
| `Decimal` | Precise decimal (financial) | `Decimal` |
| `Bool` | Boolean | `Boolean` |
| `DateTime(auto)` | Timestamp, auto-populated | `DateTime @default(now())` |
| `JSON` | Arbitrary JSON | `Json` |

### 4.2 Epistemic Type Constructors

| Constructor | Semantic | Generated Validator |
|-------------|----------|---------------------|
| `AI.Enum(V1, V2, ..., strict: true)` | AI infers one of the declared values | `z.enum(["V1","V2",...])` |
| `AI.Text(max_tokens: N)` | AI generates text, length-bounded | `z.string().max(N)` |
| `AI.Score(min: 0, max: 1)` | AI scores within range | `z.number().min(0).max(1)` |
| `AI.Embedding(dimensions: N)` | AI generates vector embedding | `z.array(z.number()).length(N)` |

### 4.3 Stochastic Routing via Confidence Thresholds

The `prior:` and `confidence_threshold:` modifiers on epistemic Enum types enable stochastic routing: when an AI call returns a `_confidence` field below the declared threshold, execution is paused and routed for human review. The transpiler generates a `bayesianUpdate()` function implementing posterior update:

```
P(value | evidence) ∝ P(evidence | value) × P(value)  [prior distribution]
```

---

## 5. Transpiler Architecture

The Epi transpiler is a three-layer pipeline:

```
    .epi source
        │
        ▼
┌───────────────────┐
│   Layer 1: Parser │  ← Lark (EBNF grammar)
│   (Deterministic) │     100% reproducible
└────────┬──────────┘
         │ AST (Pydantic models, 15 node types)
         ▼
┌───────────────────┐
│  Layer 2: Rigid   │  ← Jinja2-equivalent Python string templates
│  Code Generator   │     Entity → Prisma schema
│  (Deterministic)  │     Guard → middleware
└────────┬──────────┘     Pipeline → API routes
         │                Pulse → Zod validators
         ▼
┌───────────────────┐
│ Layer 3: Epistemic│  ← Claude API (Anthropic SDK)
│  Code Generator   │     AI.* types → inference functions
│  (Constrained)    │     Lens.Mood → Tailwind theme
└───────────────────┘
```

**Key architectural property**: The LLM is invoked ONLY in Layer 3, and ONLY for AST nodes tagged as epistemic (`AI.*` types, `Mood` declarations). Layers 1 and 2 are fully deterministic: given the same `.epi` source, they always produce the same output. This means the rigid code output is reproducible, auditable, and does not depend on LLM availability.

### 5.1 Parser (Layer 1)

The parser is implemented using **Lark**, a Python parsing library supporting EBNF grammars. The grammar (`grammar/epi.lark`) defines the complete Epi syntax. A custom Lark `Transformer` (`epi/parser/builder.py`) converts parse trees into a typed AST (`EpiProgram`) composed of 15 Pydantic model types. The Pydantic validation layer enforces structural constraints at parse time (e.g., a Guard referenced in a `Protect:` clause must be defined).

### 5.2 Rigid Code Generator (Layer 2)

The Rigid Generator produces all deterministic output:

- **`generate_prisma()`** — walks Entity nodes, emits Prisma schema models with appropriate column types and decorators for each rigid field; epistemic fields are emitted as String columns with enum constraints.
- **`generate_middleware()`** — walks Guard nodes, emits TypeScript middleware functions returning `NextResponse | null`.
- **`generate_routes()`** — walks Pipeline nodes, emits Next.js API route handlers orchestrating the declared Pulse sequence.
- **`generate_validators()`** — walks Entity nodes, emits Zod schemas for each epistemic field, including `bayesianUpdate()` functions when `prior:` is declared.
- **Scaffold generators** — emits `package.json`, `tsconfig.json`, `next.config.js`, `.env.example`, `.gitignore`, and `README.md` for complete project bootstrapping.

### 5.3 Epistemic Code Generator (Layer 3)

The Epistemic Generator handles AI-involving output:

- **`generate_pulse_stub()`** — emits TypeScript/Python functions that (a) load the prompt file from disk, (b) call the Claude API with declared temperature and max_tokens, (c) parse and validate the JSON response, (d) apply the declared fallback strategy on failure, and (e) extract `_confidence` and route to checkpoint when below threshold.
- **`generate_lens_stub()`** — emits React components with Tailwind classes mapped from `Mood` keywords through a deterministic lookup table (6 moods currently implemented deterministically; full LLM-based generation is planned for v0.4).
- **`generate_all_traces()`** — for Trace-mode Pulses, emits a `TraceState` store, per-step executor functions, and `/inspect` + `/resume` API routes.

### 5.4 CLI

The `epi` command-line interface (implemented with **Typer**) provides three commands:

```bash
epi parse <file.epi>               # Output AST as JSON
epi validate <file.epi>            # Validate syntax, show type summary
epi transpile <file.epi> [options] # Generate full-stack project
```

`epi transpile` accepts `--target {nextjs|fastapi}` and `--outdir`. It automatically copies prompt files referenced by Pulses into the output directory.

---

## 6. Evaluation

### 6.1 Case Study 1: Legal Contract Analysis

The `contrato.epi` example (30 lines) models a legal contract analysis system:

- **1 Entity** (`Contrato`) with 5 rigid fields and 1 epistemic field (`risco: AI.Enum(Alto, Medio, Baixo, strict: true)`)
- **1 Guard** (`SomenteAdvogados`, role-based access)
- **3 Pulses** (`ExtrairRisco`, `GerarResumo`, `Notificar`)
- **1 Pipeline** (`AnalisarContrato`) with retry strategy
- **1 Lens** (`Dashboard`) with table and form

From this 30-line source, `epi transpile` generates 17 files:
- `prisma/schema.prisma` — complete database schema
- `middleware/somente-advogados.ts` — auth middleware
- `app/api/analisar-contrato/route.ts` — pipeline route
- `validators/contrato.ts` — Zod schema for `risco`
- `pulses/extrair-risco.ts`, `pulses/gerar-resumo.ts`, `pulses/notificar.ts` — AI inference functions
- `components/dashboard.tsx` — UI scaffold
- `prompts/legal_scan.md` — prompt file (copied from source)
- `package.json`, `tsconfig.json`, `next.config.js`, `.env.example`, `.gitignore`, `README.md` — project bootstrap

**Lines of source vs. generated:** 30 lines of Epi → ~850 lines of TypeScript/Prisma/JSON.

### 6.2 Case Study 2: Pedagogical Assessment (EdTech)

The `edtech-pedagogico.epi` example models a student answer evaluation system using v0.3 Trace features:

- **2 Entities** (`Aluno`, `Submissao`) — with `avaliacao: AI.Enum(Correto, Parcial, Incorreto, prior: Distribution(...), confidence_threshold: 0.85)`
- **1 Guard** (`SomenteProfessores`)
- **1 Trace Pulse** (`AvaliarRespostaAluno`) with 2 named Trace steps and confidence-conditional checkpointing
- **1 Pipeline** with retry

Additional generated artifacts for the Trace Pulse:
- `lib/trace-store.ts` — in-memory TraceState store
- `traces/avaliar-resposta-aluno/compreender-enunciado.ts` — Trace 1 executor
- `traces/avaliar-resposta-aluno/avaliar-resposta.ts` — Trace 2 executor
- `app/api/traces/avaliar-resposta-aluno/[traceId]/inspect/route.ts`
- `app/api/traces/avaliar-resposta-aluno/[traceId]/resume/route.ts`
- `validators/submissao.ts` — includes `bayesianUpdateSubmissaoAvaliacao()` and `SubmissaoAvaliacaoSchemaConfidence`

### 6.3 Test Suite

The Epi transpiler has 121 unit tests across 8 test modules:

| Module | Tests | Coverage |
|--------|-------|----------|
| Parser (entities, guards, pulses) | 38 | Grammar → AST correctness |
| Rigid generator (Prisma, middleware, routes) | 29 | Template output correctness |
| Epistemic generator (pulses, validators) | 27 | AI call generation, Zod schemas |
| Trace infrastructure | 14 | TraceState store, inspect/resume routes |
| Bayesian prior / confidence | 8 | `bayesianUpdate()`, confidence schemas |
| CLI commands | 5 | parse, validate, transpile E2E |

All 121 tests pass. The test suite exercises both the contrato.epi and edtech-pedagogico.epi examples end-to-end.

---

## 7. Ethics by Design and Explainability

Epi incorporates ethical safeguards as structural properties of the language grammar, not as optional annotations or external libraries. This approach is informed by Pereira's argument that ethical constraints must be computationally enforceable — embedded in the execution model itself [PEREIRA2020].

Four grammar-level mechanisms enforce ethical properties:

1. **Mandatory fallback** (`on_fail` in every `AI.*` call): No AI inference path can silently fail. Every call declares an explicit degradation strategy, including `ManualReview` for human-in-the-loop oversight. A Pulse without `on_fail` is a syntax error.

2. **External prompt auditing** (`file("@prompts/...")`): Prompts are version-controlled artifacts, not inline strings. Every AI decision is traceable to a specific, diff-able prompt file — enabling complete decision audit trails.

3. **Guard-enforced authorization** (`Protect:` keyword): AI-driven operations are subject to the same authorization constraints as deterministic operations.

4. **Epistemic validation boundary** (`AI.*` types → Zod/Pydantic schemas): AI outputs are structurally validated before persistence. Hallucinated values outside the declared constraint are rejected at runtime, preventing bias propagation into the database.

Additionally, Trace mode (v0.3) enables **explainability by construction**: each reasoning step is named, stored, and inspectable via the generated `/inspect` route. An administrator can review the intermediate AI outputs before execution continues.

---

## 8. Related Work

| System | Relationship to Epi |
|--------|---------------------|
| **ProbZelus** [BAUDART2020] | Separates deterministic/probabilistic execution in reactive streams — Epi adapts this separation to full-stack application transpilation |
| **SlicStan** [GORINOVA2019] | Information-flow type system for probabilistic programs — Epi generalizes information-flow separation to application-level types |
| **Gradual Typing** [SIEK2006] | Mixes static/dynamic types — Epi's Rigid/Epistemic boundary adds AI inference semantics and mandatory runtime validation |
| **BAML** | Typed LLM function signatures — Epi extends beyond function-level typing to full application generation |
| **Wasp** | Full-stack DSL generating React + Node.js — Epi adds Epistemic Type System and AI-aware transpilation |
| **Wing** | Cloud-oriented programming with compile-time infrastructure — Epi focuses on AI inference orchestration rather than cloud infrastructure |

Classical languages for context:

- **Prolog** [COLMERAUER1972]: Epi's Guard primitive echoes Prolog's declarative constraints but delegates inference to external LLMs rather than implementing resolution.
- **R** [IHAKA1996]: R operates at the statistical computation layer; Epi orchestrates AI model endpoints at the application layer.
- **Julia** [BEZANSON2017]: Julia targets tensor computation and GPU kernels; Epi invokes Julia-built models as external services via Pulse.

---

## 9. Limitations and Future Work

**Current limitations:**

- **Lens.Mood** is currently implemented via a deterministic lookup table (6 moods → Tailwind class sets). Full LLM-based Tailwind theme generation from arbitrary Mood strings is planned for v0.4.
- **FastAPI target** is supported for Pulse and Entity generation but does not yet produce complete FastAPI routing scaffolding equivalent to the Next.js target.
- **Prompt validation** at parse time (warning if referenced prompt file does not exist) is implemented in the CLI but not yet as a formal type error.
- **No package manager integration**: the transpiler generates `package.json` but does not run `npm install` or `prisma generate` automatically.

**Future directions:**

1. **Type inference for Pipelines**: propagating Pulse output types through Pipeline composition to detect type mismatches at transpile time.
2. **Epi LSP**: a Language Server Protocol implementation for `.epi` files, enabling IDE support (autocomplete, hover docs, inline errors).
3. **Multi-provider support**: abstracting the Claude API call in Layer 3 to support OpenAI, Gemini, and local models via a provider interface.
4. **Formal semantics**: a denotational semantics for the Epistemic Type System, establishing a formal foundation for Theorem 1.
5. **Empirical evaluation**: a controlled study comparing development time, defect rates, and hallucination containment between Epi-generated code and conventionally written AI-augmented applications.

---

## 10. Conclusion

We presented Epi, a domain-specific language and transpiler that introduces the **Epistemic Type System** — a formal discipline for unifying deterministic and stochastic execution in a single grammar. The key insight is that AI-augmented applications require a type boundary between values that are *known* (rigid) and values that are *inferred* (epistemic), and that this boundary should be enforced structurally by the language, not by convention.

From a single `.epi` source file, the Epi transpiler generates a complete, runnable full-stack project in which:
- All rigid code (database schema, middleware, routes, validators) is produced deterministically, with no LLM involvement.
- All epistemic code (AI inference functions, Zod schemas, confidence thresholds, Bayesian update functions) is generated with mandatory validation boundaries.
- Ethics by design (mandatory fallback, external prompts, authorization enforcement, output validation) is structural, not optional.

Epi demonstrates that the challenges of building reliable AI-augmented software — hallucination containment, audit trails, authorization, fallback management — can be addressed at the language level rather than the library or convention level.

The language is available as open-source software, with full specification, 121-test suite, and two case studies:
https://github.com/RandMelville/epi-lang

---

## References

[BAUDART2020] Baudart, G., Mandel, L., Atkinson, E., Sherman, B., Pouzet, M., & Carbin, M. (2020). Reactive probabilistic programming. *Proceedings of PLDI 2020*, pp. 898–912. ACM.

[BEZANSON2017] Bezanson, J., Edelman, A., Karpinski, S., & Shah, V. B. (2017). Julia: A fresh approach to numerical computing. *SIAM Review*, 59(1), 65–98.

[COLMERAUER1972] Colmerauer, A., & Roussel, P. (1992). The birth of Prolog. *ACM SIGPLAN Notices*, 28(3), 37–52. (Original system: 1972.)

[FELLEISEN1991] Felleisen, M. (1991). On the expressive power of programming languages. *Science of Computer Programming*, 17(1–3), 35–75.

[GORINOVA2019] Gorinova, M. I., Gordon, A. D., & Sutton, C. (2019). Probabilistic programming by program transformation. *Proceedings of ICFP 2019*. ACM.

[IHAKA1996] Ihaka, R., & Gentleman, R. (1996). R: A language for data analysis and graphics. *Journal of Computational and Graphical Statistics*, 5(3), 299–314.

[MCCARTHY1960] McCarthy, J. (1960). Recursive functions of symbolic expressions and their computation by machine, Part I. *Communications of the ACM*, 3(4), 184–195.

[PEREIRA2020] Pereira, L. M. (2020). *Programming Machine Ethics*. Springer.

[PEREIRA2016] Pereira, L. M., & Saptawijaya, A. (2016). *Programming Machine Ethics*. Studies in Applied Philosophy, Epistemology and Rational Ethics, vol 26. Springer, Cham.

[PIERCE] Pierce, B. C. (2002). *Types and Programming Languages*. MIT Press.

[SIEK2006] Siek, J. G., & Taha, W. (2006). Gradual typing for functional languages. *Proceedings of the Scheme and Functional Programming Workshop*.

[STAN2017] Carpenter, B., Gelman, A., Hoffman, M. D., Lee, D., Goodrich, B., Betancourt, M., ... & Riddell, A. (2017). Stan: A probabilistic programming language. *Journal of Statistical Software*, 76(1).

[WASP2022] Šošić, M. (2022). Wasp: A Rails-like framework for React, Node.js and Prisma. https://wasp-lang.dev

[WING2024] Lefkovits, E. (2024). Wing: A programming language for the cloud. https://winglang.io
