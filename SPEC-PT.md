# Especificação da Linguagem Epi v0.3

**Epi — Epistemic Programming Interface**
*Uma Linguagem Zero-Stack Orientada a Intenção com Sistema de Tipos Epistêmico*

**Autor:** Randerson Rebouças (UFRGS — Doutorado em Computação na Educação)
**Versão:** 0.3
**Data:** 2026-03-25
**Licença:** Apache 2.0

---

## 1. Motivação

Modelos de Linguagem de Grande Escala (LLMs) geram e consomem código-fonte com frequência crescente. No entanto, as linguagens de programação tradicionais (Python, JavaScript, SQL) apresentam três problemas fundamentais para o desenvolvimento mediado por LLMs:

1. **Alta Entropia**: A mesma intenção pode ser expressa de dezenas de formas sintaticamente válidas, aumentando o consumo de tokens e a probabilidade de alucinação.
2. **Separação Forçada de Stack**: Desenvolvedores precisam manter modelos mentais separados para frontend, backend, banco de dados e inferência com IA — cada um com sua própria linguagem e convenções.
3. **Ausência de Fronteira Epistêmica**: Não existe forma de distinguir, dentro da mesma gramática, o que é *conhecido* (determinístico — ex.: um schema de banco de dados) do que deve ser *inferido* (estocástico — ex.: uma classificação por IA), levando à corrupção de dados quando LLMs alucinam em contextos rígidos.

A Epi resolve os três problemas ao fornecer uma **gramática única** com **cinco primitivas** e um **Sistema de Tipos Epistêmico** que separa formalmente a execução determinística da estocástica.

---

## 2. Conceito Central: O Sistema de Tipos Epistêmico

A inovação central da Epi é o **Sistema de Tipos Epistêmico** — uma disciplina de tipos que classifica cada valor de um programa em um de dois domínios epistêmicos:

### 2.1 Tipos Rígidos (Domínio Determinístico)

Tipos rígidos representam valores completamente determinados em tempo de compilação/transpilação. Eles mapeiam diretamente para colunas de banco de dados, schemas de API e configuração estática.

```
UUID(auto)    → identificador único gerado automaticamente
Text          → valor string
Int           → valor inteiro
Float         → valor de ponto flutuante
Decimal       → decimal preciso (financeiro)
Bool          → booleano
DateTime(auto)→ timestamp, preenchido automaticamente
JSON          → estrutura JSON arbitrária
```

**Propriedade**: Um tipo rígido SEMPRE transpila para a mesma saída. Sem envolvimento de LLM.

### 2.2 Tipos Epistêmicos (Domínio Estocástico)

Tipos epistêmicos representam valores que requerem inferência de IA, mas são **constrangidos** por schemas de validação formais (Zod, Pydantic) gerados em tempo de transpilação.

```
AI.Enum(Valor1, Valor2, ..., strict: true)  → IA infere, mas deve corresponder ao enum
AI.Text(max_tokens: N)                       → IA gera texto, com limite de tamanho
AI.Score(min: 0, max: 1)                     → IA pontua dentro de um intervalo
AI.Embedding(dimensions: N)                  → IA gera embedding vetorial
```

**Propriedade**: Um tipo epistêmico gera TANTO a chamada de inferência QUANTO o schema de validação de runtime. A IA pode alucinar — mas a validação captura.

### 2.3 Prior de Distribuição (v0.3)

Campos epistêmicos do tipo Enum podem declarar um **prior Bayesiano** — a distribuição de probabilidade inicial sobre os valores antes de qualquer evidência ser observada. Isso habilita roteamento estocástico e geração de funções de atualização Bayesiana.

```epi
avaliacao: AI.Enum(Correto, Parcial, Incorreto,
    prior: Distribution(Correto: 0.40, Parcial: 0.45, Incorreto: 0.15),
    confidence_threshold: 0.85
)
```

**Efeitos da transpilação:**
- `prior` → gera função TypeScript `bayesianUpdate{Entidade}{Campo}()` implementando posterior ∝ verossimilhança × prior, normalizado
- `confidence_threshold` → gera schema Zod companion `{Schema}Confidence` com `requiresReview: confiança < limiar`

**Aplicação em dois níveis**: `confidence_threshold` no tipo da Entidade é a constraint da *camada de dados* (validação persistida). `on_low_confidence` dentro de uma chamada Execute é a constraint de *roteamento em runtime* (dispara revisão humana no meio do pipeline). Ambos podem coexistir para defesa em profundidade.

### 2.4 A Fronteira Epistêmica

Dentro de uma mesma Entity, tipos rígidos e epistêmicos coexistem:

```epi
Entity Contrato {
    id: UUID(auto),              // Rígido — determinístico
    documento: Text,             // Rígido — determinístico
    risco: AI.Enum(Alto, Medio, Baixo, strict: true)  // Epistêmico — inferido por IA, validado
}
```

O transpilador gera:
- **Schema Prisma/SQLAlchemy** para campos rígidos (baseado em templates, sem LLM)
- **Validador Zod/Pydantic** para campos epistêmicos (baseado em templates, sem LLM)
- **Chamada de inferência LLM** para população de campos epistêmicos (assistida por LLM, constrangida)

---

## 3. As Cinco Primitivas

### 3.1 Entity

Define schemas de dados com anotações de tipos epistêmicos.

**Sintaxe:**
```ebnf
entity ::= "Entity" IDENT "{" field ("," field)* "}"
field  ::= IDENT ":" type_expr
type_expr ::= rigid_type | epistemic_type
```

**Exemplo:**
```epi
Entity Advogado {
    id: UUID(auto),
    nome: Text,
    oab: Text,
    especialidade: AI.Text(max_tokens: 50)
}
```

**Transpilação:**
- Campos rígidos → colunas de banco de dados (modelo Prisma / modelo SQLAlchemy)
- Campos epistêmicos → colunas de banco de dados + validação de runtime + função de inferência com IA

---

### 3.2 Guard

Declara constraints de autenticação e autorização que transpilam para middleware.

**Sintaxe:**
```ebnf
guard      ::= "Guard" IDENT "{" "Condition:" condition_expr "}"
condition  ::= dotted_name COMPARATOR literal
```

**Exemplo:**
```epi
Guard SomenteAdvogados {
    Condition: Auth.Role == "Lawyer"
}
```

**Transpilação:**
- Next.js → função middleware retornando `NextResponse | null` (null = acesso permitido, NextResponse(403) = acesso negado)
- FastAPI → função de dependência com `HTTPException(403)`

**Decisão de design**: O Guard retorna `NextResponse | null` (não void), garantindo que o padrão de retorno antecipado seja enforçado no código gerado. A rota chamadora verifica `if (guard) return guard;` antes de prosseguir.

---

### 3.3 Pulse

A primitiva de execução — onde a lógica ocorre e a alucinação é controlada. Toda interação com IA é explícita, com parâmetros obrigatórios.

Um Pulse possui dois modos de execução:

**Modo clássico** (`Process:`): chamada de IA em único passo, saída imediata.

**Modo Trace** (`Trace`): pipeline de múltiplos passos, observável, onde cada passo é nomeado, interruptível e inspecionável. Usado quando o raciocínio deve ser decomposto em sub-tarefas auditáveis.

**Sintaxe:**
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

**Funções de IA:** `scan`, `classify`, `summarize`, `extract`, `generate`, `embed`, `reason`

A função `reason` sinaliza intenção de raciocínio em cadeia de pensamento (mesma chamada de API, anotação semântica diferente para fins de rastreamento e auditoria).

**Parâmetros obrigatórios da chamada AI:**
| Parâmetro | Propósito |
|-----------|-----------|
| `source` | Referência ao dado de entrada (ex.: `Input.documento`) |
| `prompt` | Arquivo de prompt externo via `file("@prompts/...")` |
| `temperature` | Controla aleatoriedade (menor = mais determinístico) |
| `on_fail` | Estratégia de fallback quando a IA falha |

**Parâmetros específicos de Trace:**

| Construto | Propósito |
|-----------|-----------|
| `Expose: campo1, campo2` | Campos na saída JSON da IA disponibilizados para Traces subsequentes |
| `Checkpoint: ReviewRequired(...)` | Pausa a execução para revisão humana antes de prosseguir |
| `on_low_confidence: Checkpoint.ReviewRequired(...)` | Pausa condicional — dispara apenas quando `_confidence < limiar` |

**Estratégias de Fallback:**
- `Fallback.ManualReview(Queue: "...")` — encaminha para fila de revisão humana
- `Fallback.ReturnEmpty` — retorna vazio/null
- `Fallback.ReturnDefault(value: "...")` — retorna valor padrão
- `Fallback.Retry(max: N)` — tenta novamente com backoff
- `Fallback.Escalate(to: "...")` — escala para outro sistema

**Exemplo — Pulse Clássico:**
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

**Decisão de design chave**: Ao exigir `prompt: file(...)`, a Epi força que os prompts sejam arquivos externos e versionados — não strings inline. Isso possibilita auditoria de prompts e testes A/B.

### 3.3.1 Trace: Depuração Epistêmica (v0.3)

Trace é o mecanismo da Epi para **depuração epistêmica** — a capacidade de observar, interromper e validar passos intermediários de raciocínio dentro de um Pulse. Isso endereça um problema fundamental em sistemas aumentados por IA: quando uma decisão complexa falha, não há como identificar *qual passo de raciocínio* falhou.

**Propriedades-chave do Trace:**

1. **Observável**: Cada passo Trace é nomeado e sua saída é armazenada em um registro `TraceState`, acessível via a rota de API `/inspect` gerada.

2. **Interruptível**: Uma declaração `Checkpoint` pausa a execução antes do próximo passo, armazenando o estado atual para revisão humana. A execução é retomada via a rota `/resume` gerada apenas após aprovação humana explícita.

3. **Encadeável**: A declaração `Expose:` torna campos específicos da saída de um Trace disponíveis como contexto para o próximo Trace.

**Estratégias de Checkpoint:**
- `Checkpoint: ReviewRequired(...)` — pausa incondicional (sempre requer aprovação humana)
- `on_low_confidence: Checkpoint.ReviewRequired(...)` — pausa condicional (dispara apenas quando o campo `_confidence` da IA está abaixo de um limiar)

**O contrato `_confidence`**: Prompts usados em passos Trace devem incluir um campo `_confidence` (0.0–1.0) em sua saída JSON. Isso é enforçado por convenção (documentado no arquivo de prompt) e extraído em runtime pelo código de execução Trace gerado.

**Infraestrutura gerada para um Pulse com Trace:**
- `lib/trace-store.ts` — store em memória para `TraceState` (indexado por traceId, inclui `originalInput`, saídas dos passos e `pipelineStatus`)
- `traces/{pulse}/{trace}.ts` — função de execução para cada passo Trace (chama Claude, extrai `_confidence`, salva estado, verifica `shouldPause`)
- `app/api/traces/{pulse}/[traceId]/inspect/route.ts` — rota GET para UI de revisão humana
- `app/api/traces/{pulse}/[traceId]/resume/route.ts` — rota POST para aceitar a saída de um passo e encadear ao próximo Trace

**Exemplo — Pulse com Trace:**
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

Compõe Pulses em fluxos de negócio sequenciais com tratamento de erros.

**Sintaxe:**
```ebnf
pipeline ::= "Pipeline" IDENT "{" "Flow:" IDENT ("->" IDENT)+ error_strategy? "}"
```

**Exemplo:**
```epi
Pipeline AnalisarContrato {
    Flow: ExtrairRisco -> GerarResumo -> Notificar
    On_Error: Retry(max: 3, backoff: exponential)
}
```

**Transpilação:** Gera uma rota de API que orquestra as chamadas de Pulse em sequência, com a estratégia de tratamento de erros declarada.

---

### 3.5 Lens

Declara UI por intenção semântica (Mood) com um escape hatch para injeção de código nativo.

**Sintaxe:**
```ebnf
lens    ::= "Lens" IDENT "{" lens_body "}"
lens_body ::= ("Mood:" STRING)? "Display:" display_items ("Inject:" STRING)?
```

**Tipos de widget:** `Table`, `Form`, `Card`, `List`, `Chart`, `Button`, `Input`, `Modal`

**Exemplo:**
```epi
Lens Dashboard {
    Mood: "Clean, Legal-Tech, Professional"
    Display:
        Table(Contrato, columns: [titulo, valor, risco]),
        Form(Contrato) -> Button("Analisar").trigger(ExtrairRisco)
    Inject: "<footer class='text-sm'>© 2026</footer>"
}
```

**Transpilação:**
- `Mood` → LLM gera estilização/tema (camada epistêmica)
- `Display` → estrutura de componentes (templates determinísticos)
- `Inject` → HTML/JSX bruto passado diretamente (escape hatch)

---

## 4. Arquitetura do Transpilador

A Epi utiliza uma arquitetura de **transpilador de três camadas**:

```
    Fonte .epi
        │
        ▼
┌───────────────────┐
│  Camada 1: Parser │  ← Lark (gramática EBNF)
│  (Determinístico) │     100% reprodutível
└────────┬──────────┘
         │ AST (modelos Pydantic)
         ▼
┌───────────────────┐
│  Camada 2: Gerador│  ← Templates Jinja2
│  Rígido           │     Entity → Prisma
│  (Determinístico) │     Guard → middleware
└────────┬──────────┘     Pipeline → rotas
         │
         ▼
┌───────────────────┐
│ Camada 3: Gerador │  ← LLM (Claude API)
│  Epistêmico       │     Tipos AI.* → código de inferência
│  (Constrito)      │     Lens.Mood → estilização de UI
└───────────────────┘     Trace → infraestrutura de depuração epistêmica
```

**Propriedade chave**: O LLM é invocado APENAS na Camada 3, e APENAS para nós AST marcados como epistêmicos (`AI.*`, `Mood`, `Trace`). O parser e o gerador rígido são totalmente determinísticos.

---

## 5. Extensão de Arquivo

Arquivos fonte Epi utilizam a extensão `.epi`.

---

## 6. Exemplos Completos

### 6.1 Pulse Clássico — Análise Jurídica

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

### 6.2 Pulse com Trace — Avaliação Pedagógica (v0.3)

Este exemplo demonstra os recursos v0.3: Trace, Checkpoint, prior de Distribuição e confidence_threshold.

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

**Artefatos gerados para este programa:**
- `prisma/schema.prisma` — modelos Aluno e Submissao
- `validators/submissao.ts` — schemas Zod para `avaliacao` e `justificativa`
- `validators/submissao.ts` — função `bayesianUpdateSubmissaoAvaliacao()` (gerada de `prior:`)
- `validators/submissao.ts` — schema `SubmissaoAvaliacaoSchemaConfidence` (gerado de `confidence_threshold:`)
- `lib/trace-store.ts` — store TraceState
- `traces/avaliar-resposta-aluno/compreender-enunciado.ts` — executor do Trace 1
- `traces/avaliar-resposta-aluno/avaliar-resposta.ts` — executor do Trace 2
- `app/api/traces/avaliar-resposta-aluno/[traceId]/inspect/route.ts`
- `app/api/traces/avaliar-resposta-aluno/[traceId]/resume/route.ts`

---

## 7. Trabalhos Relacionados

A Epi se apoia e se distingue de quatro linhagens de trabalhos anteriores: (a) linguagens de programação probabilística, (b) sistemas de tipagem gradual, (c) DSLs orientadas a LLM e (d) ferramentas de geração de código full-stack.

| Sistema | Relação com a Epi |
|---------|-------------------|
| **ProbZelus** (Baudart et al., PLDI 2020) | Separa execução determinística/probabilística em streams reativos — Epi adapta essa separação para transpilação full-stack de aplicações |
| **SlicStan** (Gorinova et al., POPL 2019) | Sistema de tipos com fluxo de informação para programas probabilísticos — Epi generaliza a separação para tipos de nível de aplicação (banco de dados vs. inferido por IA) |
| **Tipagem Gradual** (Siek & Taha, 2006) | Mistura tipos estáticos/dinâmicos via o tipo `?` — a fronteira Rígido/Epistêmico da Epi é estruturalmente análoga, mas substitui o eixo estático–dinâmico por determinístico–estocástico |
| **BAML** (Boundary ML) | DSL para assinaturas de funções LLM tipadas — Epi estende para geração completa de aplicação a partir de uma única declaração |
| **Wasp** (wasp-lang) | DSL full-stack gerando React + Node.js — Epi adiciona o Sistema de Tipos Epistêmico; Wasp não distingue valores determinísticos de inferidos por IA |
| **Lisp** (McCarthy, 1960) | Compartilha a filosofia de primitivas mínimas (7 formas do Lisp, 5 primitivas da Epi), mas opera na camada de orquestração, não computação simbólica |
| **Prolog** (Colmerauer & Roussel, 1972) | A primitiva Guard ecoa os constraints declarativos do Prolog, mas Epi delega inferência a LLMs externos |
| **R** / **Julia** | Operam na camada de computação de modelos; Epi opera na camada de orquestração e invoca esses sistemas via Pulse |

---

## 8. Ética por Design e Explicabilidade

A Epi incorpora salvaguardas éticas e explicabilidade de decisões como propriedades estruturais da linguagem, não como bibliotecas ou convenções opcionais.

### 8.1 Salvaguardas Éticas Estruturais

| Mecanismo | Elemento da Gramática | Propriedade Ética |
|-----------|----------------------|-------------------|
| **Fallback obrigatório** | `on_fail` em toda chamada `AI.*` | Nenhuma decisão de IA pode falhar silenciosamente |
| **Auditoria de prompts externos** | `file("@prompts/...")` | Prompts são artefatos versionados, auditáveis e rastreáveis |
| **Autorização via Guard** | Primitiva `Guard` com `Protect:` | Operações de IA sujeitas aos mesmos constraints de autorização que operações determinísticas |
| **Fronteira de validação epistêmica** | Tipos `AI.*` → schemas Zod/Pydantic | Saídas de IA validadas estruturalmente antes da persistência |
| **Depuração epistêmica** (v0.3) | `Trace` + `Checkpoint` | Raciocínio intermediário observável, interruptível e auditável por humanos |

### 8.2 Propriedades de Explicabilidade

1. **Rastreabilidade**: Cada inferência de IA é rastreável a um Pulse/Trace específico com input, prompt, temperatura e fallback declarados.
2. **Reprodutibilidade**: `temperature` obrigatório + prompt externo + fonte declarada permite reprodução das condições de qualquer decisão.
3. **Auditabilidade**: LLM invocado APENAS na Camada 3. Auditor precisa apenas inspecionar Camada 3 + arquivos de prompt.
4. **Override humano**: `Fallback.ManualReview` e `Checkpoint.ReviewRequired` como construtos de primeira classe, não workarounds.

### 8.3 Referências

- Pereira, L. M. (2020). *Programming Machine Ethics*. Springer.
- Pereira, L. M., & Saptawijaya, A. (2016). *Programming Machine Ethics*. Studies in Applied Philosophy, Epistemology and Rational Ethics, vol 26. Springer, Cham.
- Floridi, L., & Cowls, J. (2019). A unified framework of five principles for AI in society. *Harvard Data Science Review*, 1(1).

---

## 9. Fronteira de Escopo: Orquestração vs. Computação

A Epi é uma **linguagem de orquestração de aplicação**. Ela declara *o que* uma aplicação aumentada por IA deve fazer e delega *como* a engines especializadas.

### 9.1 O que a Epi Trata

| Preocupação | Mecanismo | Camada |
|-------------|-----------|--------|
| Definição de schema de dados | Entity → Prisma/SQLAlchemy | Camada 2 (Determinístico) |
| Autenticação e autorização | Guard → middleware | Camada 2 (Determinístico) |
| Orquestração de inferência com IA | Pulse → chamada de API LLM com validação | Camada 3 (Epistêmico) |
| Composição de fluxos de negócio | Pipeline → rota com tratamento de erros | Camada 2 (Determinístico) |
| Declaração de UI por intenção | Lens → scaffold de componente + estilização por IA | Camadas 2+3 |
| Validação de saídas de IA em runtime | Tipos epistêmicos → schemas Zod/Pydantic | Camada 2 (Determinístico) |
| Raciocínio intermediário auditável | Trace + TraceState + rotas inspect/resume | Camada 3 (Epistêmico) |
| Trilha de auditoria de decisões | Prompts externos + estratégias de fallback | Enforçado pela gramática |

### 9.2 O que a Epi Delega

| Preocupação | Delegado Para |
|-------------|---------------|
| Operações tensoriais, álgebra linear | PyTorch, TensorFlow, JAX |
| Diferenciação automática | Bibliotecas autograd |
| Otimização de kernels GPU/TPU | CUDA, XLA, Metal |
| Treinamento e fine-tuning de modelos | MLflow, Kubeflow, W&B |
| Computação estatística | R, Julia, Python (scipy, statsmodels) |
| Raciocínio simbólico e unificação | Prolog, Datalog, knowledge graphs |
| Paralelismo de baixo nível | Runtime da linguagem alvo (Node.js, asyncio) |

### 9.3 O Princípio de Composição

> *"O poder expressivo de uma linguagem é determinado não apenas pelo que ela pode expressar, mas pelo que ela pode seguramente excluir."*
> — cf. Felleisen, M. (1991). "On the Expressive Power of Programming Languages." *Science of Computer Programming*, 17(1-3), pp. 35–75.

---

## 10. Licença

Apache License 2.0 — Copyright (c) 2026 Randerson Rebouças
