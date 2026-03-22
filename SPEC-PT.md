# Especificação da Linguagem Epi v0.2

**Epi — Epistemic Programming Interface**
*Uma Linguagem Zero-Stack Orientada a Intenção com Sistema de Tipos Epistêmico*

**Autor:** Randerson Rebouças (UFRGS — Doutorado em Computação na Educação)
**Versão:** 0.2
**Data:** 2026-03-19
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
AI.Classification(labels: [...])             → IA classifica em labels fixos
AI.Score(min: 0, max: 1)                     → IA pontua dentro de um intervalo
AI.Embedding(dimensions: N)                  → IA gera embedding vetorial
```

**Propriedade**: Um tipo epistêmico gera TANTO a chamada de inferência QUANTO o schema de validação de runtime. A IA pode alucinar — mas a validação captura.

### 2.3 A Fronteira Epistêmica

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
- Next.js → função de middleware verificando `session.user.role`
- FastAPI → função de dependência com `HTTPException(403)`

---

### 3.3 Pulse

A primitiva de execução — onde a lógica ocorre e a alucinação é controlada. Toda interação com IA é explícita, com parâmetros obrigatórios.

**Sintaxe:**
```ebnf
pulse      ::= "Pulse" IDENT "{" pulse_body "}"
pulse_body ::= "Input:" IDENT
               ("Protect:" dotted_name)?
               "Process:" process_step+
               ("Output:" type_or_ref)?
process_step ::= "Execute:" ai_call
ai_call    ::= "AI." FUNC "(" named_args ")"
```

**Parâmetros obrigatórios da chamada AI:**
| Parâmetro | Propósito |
|-----------|-----------|
| `source` | Referência ao dado de entrada |
| `prompt` | Arquivo de prompt externo via `file("@prompts/...")` |
| `temperature` | Controla aleatoriedade (menor = mais determinístico) |
| `on_fail` | Estratégia de fallback quando a IA falha |

**Estratégias de Fallback:**
- `Fallback.ManualReview(Queue: "...")` — encaminha para fila de revisão humana
- `Fallback.ReturnEmpty` — retorna vazio/null
- `Fallback.ReturnDefault(value: "...")` — retorna valor padrão
- `Fallback.Retry(max: N)` — tenta novamente com backoff
- `Fallback.Escalate(to: "...")` — escala para outro sistema

**Exemplo:**
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
└───────────────────┘
```

**Propriedade chave**: O LLM é invocado APENAS na Camada 3, e APENAS para nós AST marcados como epistêmicos (`AI.*`, `Mood`). O parser e o gerador rígido são totalmente determinísticos.

---

## 5. Extensão de Arquivo

Arquivos fonte Epi utilizam a extensão `.epi`.

---

## 6. Exemplo Completo

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

## 7. Trabalhos Relacionados

A Epi se apoia e se distingue de quatro linhagens de trabalhos anteriores: (a) linguagens de programação probabilística, (b) sistemas de tipagem gradual, (c) DSLs orientadas a LLM e (d) ferramentas de geração de código full-stack. A tabela abaixo inclui adicionalmente linguagens clássicas que abordam preocupações adjacentes — IA simbólica (Lisp, Prolog), computação estatística (R) e computação científica de alto desempenho (Julia) — para clarificar as fronteiras arquiteturais da Epi.

| Sistema | Relação com a Epi |
|---------|-------------------|
| **ProbZelus** (Baudart et al., PLDI 2020) | Separa execução determinística/probabilística em streams reativos — Epi adapta essa separação para transpilação full-stack de aplicações |
| **SlicStan** (Gorinova et al., POPL 2019) | Sistema de tipos com fluxo de informação para programas probabilísticos — Epi generaliza a separação de fluxo de informação para tipos de nível de aplicação (banco de dados vs. inferido por IA) |
| **Tipagem Gradual** (Siek & Taha, 2006) | Mistura tipos estáticos/dinâmicos via o tipo `?` — a fronteira Rígido/Epistêmico da Epi é estruturalmente análoga, mas substitui o eixo estático–dinâmico por um eixo determinístico–estocástico, adicionando semânticas de inferência por IA e validação obrigatória em runtime |
| **BAML** (Boundary ML) | DSL para assinaturas de funções LLM tipadas — Epi estende para além da tipagem em nível de função para geração completa de aplicação (banco de dados, rotas, UI) a partir de uma única declaração |
| **Wasp** (wasp-lang) | DSL full-stack gerando React + Node.js — Epi adiciona o Sistema de Tipos Epistêmico e transpilação com consciência de IA; Wasp não possui mecanismo para distinguir valores determinísticos de inferidos por IA |
| **Lisp** (McCarthy, 1960) | Pioneira da IA simbólica e homoiconicidade — Epi compartilha a filosofia de primitivas mínimas (7 formas do Lisp, 5 primitivas da Epi), mas opera na camada de orquestração de aplicação ao invés da camada de computação simbólica; Epi não implementa avaliação simbólica nem expansão de macros |
| **Prolog** (Colmerauer & Roussel, 1972) | Programação lógica via cláusulas de Horn e unificação — a primitiva Guard da Epi ecoa os constraints declarativos do Prolog, mas a Epi delega a inferência a LLMs externos ao invés de implementar seu próprio motor de resolução; o escopo da Epi é geração de aplicação, não prova automática de teoremas |
| **R** (Ihaka & Gentleman, 1996) | Linguagem específica de domínio para computação estatística — R opera na camada de análise de dados e ajuste de modelos; Epi opera na camada de orquestração de aplicação e delega computação estatística a endpoints de modelos de IA via Pulse |
| **Julia** (Bezanson et al., 2017) | Computação científica de alto desempenho com dispatch múltiplo — Julia tem como alvo a camada de computação de modelos (operações tensoriais, diferenciação automática, kernels GPU); Epi tem como alvo a camada de orquestração de aplicação e invocaria modelos construídos em Julia como serviços externos via Pulse |

---

## 8. Ética por Design e Explicabilidade

A Epi incorpora salvaguardas éticas e explicabilidade de decisões como propriedades estruturais da linguagem, não como bibliotecas ou convenções opcionais. Essa abordagem é informada pela proposta de Pereira para programar ética em sistemas de IA (Pereira, 2020; Pereira & Saptawijaya, 2016), que argumenta que constraints éticos devem ser *computacionalmente enforceáveis* — embutidos no modelo de execução em si, não delegados a auditorias post-hoc.

### 8.1 Salvaguardas Éticas Estruturais

A Epi enforça constraints éticos através de quatro mecanismos que são elementos obrigatórios da gramática, não anotações opcionais:

| Mecanismo | Elemento da Gramática | Propriedade Ética |
|-----------|----------------------|-------------------|
| **Fallback obrigatório** | Parâmetro `on_fail` em toda chamada `AI.*` | Nenhuma decisão de IA pode falhar silenciosamente. Todo caminho de inferência tem uma estratégia explícita de degradação, incluindo `ManualReview` para supervisão humana no loop |
| **Auditoria de prompts externos** | Sintaxe `file("@prompts/...")` | Prompts são artefatos versionados, não strings inline. Todo prompt pode ser auditado, comparado, revisado e submetido a testes A/B — criando uma trilha completa de auditoria de decisões |
| **Autorização via Guard** | Primitiva `Guard` com referência `Protect:` | Operações dirigidas por IA estão sujeitas aos mesmos constraints de autorização que operações determinísticas. O transpilador rejeita um Pulse que referencia um Guard inexistente |
| **Fronteira de validação epistêmica** | Tipos `AI.*` → schemas Zod/Pydantic | Saídas de IA são estruturalmente validadas antes da persistência. Um valor alucinado fora do enum/intervalo/schema declarado é rejeitado em runtime, impedindo a propagação de viés no banco de dados |

### 8.2 Propriedades de Explicabilidade

Toda decisão de IA feita através da Epi é explicável por construção:

1. **Rastreabilidade**: Cada inferência de IA é rastreável a um Pulse específico, que declara sua Entity de entrada, arquivo de prompt, temperatura e estratégia de fallback. Não existem chamadas implícitas de IA.

2. **Reprodutibilidade**: O parâmetro `temperature` é obrigatório e explícito. Combinado com o arquivo de prompt externo e a fonte de entrada declarada, um terceiro pode reproduzir as condições sob as quais qualquer decisão de IA foi tomada.

3. **Auditabilidade**: A arquitetura de transpilador de três camadas garante que todo código determinístico (schemas de banco de dados, rotas de API, middleware) é gerado sem envolvimento de LLM. Apenas a Camada 3 (Epistêmica) envolve IA, e suas saídas são constrangidas por validadores da Camada 2. Um auditor precisa apenas inspecionar as saídas da Camada 3 e os arquivos de prompt para compreender todo comportamento influenciado por IA.

4. **Override humano**: A estratégia `Fallback.ManualReview(Queue: "...")` encaminha explicitamente decisões incertas para revisores humanos, implementando o padrão human-in-the-loop como um construto de primeira classe da linguagem, ao invés de um workaround em nível de aplicação.

### 8.3 Referências

- Pereira, L. M. (2020). *Programming Machine Ethics*. Springer.
- Pereira, L. M., & Saptawijaya, A. (2016). *Programming Machine Ethics*. Studies in Applied Philosophy, Epistemology and Rational Ethics, vol 26. Springer, Cham.
- Floridi, L., & Cowls, J. (2019). A unified framework of five principles for AI in society. *Harvard Data Science Review*, 1(1).

---

## 9. Fronteira de Escopo: Orquestração vs. Computação

A Epi é uma **linguagem de orquestração de aplicação**. Ela declara *o que* uma aplicação aumentada por IA deve fazer e delega *como* a engines especializadas. Esta seção define formalmente a fronteira entre o que a Epi trata e o que ela delega.

### 9.1 O que a Epi Trata

| Preocupação | Mecanismo | Camada |
|-------------|-----------|--------|
| Definição de schema de dados | Entity → Prisma/SQLAlchemy | Camada 2 (Determinístico) |
| Autenticação e autorização | Guard → middleware | Camada 2 (Determinístico) |
| Orquestração de inferência com IA | Pulse → chamada de API LLM com validação | Camada 3 (Epistêmico) |
| Composição de fluxos de negócio | Pipeline → rota com tratamento de erros | Camada 2 (Determinístico) |
| Declaração de UI por intenção | Lens → scaffold de componente + estilização por IA | Camadas 2+3 |
| Validação de saídas de IA em runtime | Tipos epistêmicos → schemas Zod/Pydantic | Camada 2 (Determinístico) |
| Trilha de auditoria de decisões | Prompts externos + estratégias de fallback | Enforçado pela gramática |

### 9.2 O que a Epi Delega

| Preocupação | Delegado Para | Justificativa |
|-------------|---------------|---------------|
| Operações tensoriais, álgebra linear | PyTorch, TensorFlow, JAX | A Epi opera acima da camada de computação de modelos. Um Pulse invoca um endpoint de modelo; não implementa o modelo |
| Diferenciação automática | Bibliotecas autograd (PyTorch, JAX) | Diferenciação é uma propriedade do grafo de computação, não do grafo de orquestração |
| Otimização de kernels GPU/TPU | CUDA, XLA, Metal via frameworks ML | Otimização em nível de hardware é ortogonal à declaração de intenção em nível de aplicação |
| Treinamento e fine-tuning de modelos | Pipelines ML (MLflow, Kubeflow, W&B) | Treinamento produz modelos; Epi consome modelos. A fronteira de ciclo de vida está no endpoint da API do modelo |
| Computação estatística | R, Julia, Python (scipy, statsmodels) | Análise estatística é uma preocupação computacional; Epi orquestra os resultados da computação |
| Raciocínio simbólico e unificação | Prolog, Datalog, engines de knowledge graph | A primitiva Guard da Epi lida com constraints declarativos para autorização; raciocínio simbólico completo é delegado a engines especializadas |
| Paralelismo de baixo nível e threading | Runtime da linguagem alvo (event loop Node.js, asyncio Python) | O Pipeline da Epi declara composição sequencial; o transpilador gera as primitivas de concorrência apropriadas no alvo |

### 9.3 O Princípio de Composição

A fronteira de escopo da Epi segue o **princípio de composição**: a linguagem alcança expressividade máxima não ao incorporar todo paradigma computacional, mas ao se compor de forma limpa com ferramentas especializadas em interfaces bem definidas.

Um exemplo concreto: um desenvolvedor construindo um sistema de análise de contratos com um modelo NLP customizado faria:

1. **Treinar o modelo** em PyTorch/JAX (fora da Epi)
2. **Deployar** como um endpoint de API (ex.: FastAPI + Docker)
3. **Invocá-lo da Epi** via Pulse com o endpoint como provedor de IA
4. **Validar sua saída** via o Sistema de Tipos Epistêmico (dentro da Epi)

Isso é análogo ao SQL declarando `SELECT * FROM contratos WHERE risco = 'alto'` sem especificar o algoritmo de travessia da B-tree. O poder está na declaração, não na computação.

> *"O poder expressivo de uma linguagem é determinado não apenas pelo que ela pode expressar, mas pelo que ela pode seguramente excluir."*
> — cf. Felleisen, M. (1991). "On the Expressive Power of Programming Languages." *Science of Computer Programming*, 17(1-3), pp. 35–75.

---

## 10. Licença

Apache License 2.0 — Copyright (c) 2026 Randerson Rebouças
