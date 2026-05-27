# Manual Técnico do Epi — Para o Autor

> **Para uso pessoal de Randerson Rebouças.**
> Não é documentação pública. É a versão "tudo o que você precisa para defender, explicar, e estender o Epi" — escrita em português, com analogias e definições inline para os conceitos de baixo nível que você admitiu não dominar ainda.
>
> Leia na ordem ou pule direto para a seção que precisa. Os blocos **[CONCEITO]** definem termos técnicos no momento em que aparecem.

---

## Sumário

1. [Conceitos-base que você precisa dominar](#1-conceitos-base)
2. [O que é o Epi, em camadas](#2-o-que-é-o-epi)
3. [O sistema de tipos epistêmico (a contribuição central)](#3-o-sistema-de-tipos-epistêmico)
4. [A arquitetura do transpilador](#4-a-arquitetura-do-transpilador)
5. [O que o transpilador realmente gera](#5-o-que-o-transpilador-gera)
6. [Trace + Checkpoint (a contribuição da Rosa)](#6-trace--checkpoint)
7. [Computação estocástica (a contribuição do Dante)](#7-computação-estocástica)
8. [O que o Epi NÃO faz e NÃO tenta fazer](#8-o-que-o-epi-não-faz)
9. [As decisões de design e seus trade-offs](#9-decisões-de-design)
10. [Como argumentar pelo Epi (defesa contra críticas comuns)](#10-como-argumentar)
11. [Glossário](#11-glossário)
12. [Apêndice — referências para aprofundar](#12-apêndice)

---

## 1. Conceitos-base

Esta seção define os conceitos de PL e compiladores que aparecem repetidamente quando se fala de Epi. Se você já domina, pule. Se não, leia — vai mudar a forma como você ouve críticas e responde.

### 1.1 Sistema de tipos

**[CONCEITO]** Um **sistema de tipos** é o conjunto de regras de uma linguagem que classifica os valores que existem nela e diz quais combinações são permitidas. Em Python, `1 + "a"` é um erro de tipo. Em JavaScript, `1 + "a"` resulta em `"1a"` — mesma operação, sistemas de tipos diferentes.

A função principal de um sistema de tipos não é "ajudar a programar" — é **rejeitar programas que iriam quebrar em tempo de execução**. Em Pierce (livro de referência: *Types and Programming Languages*, MIT Press 2002), há a frase canônica: *"a type system is a tractable syntactic method for proving the absence of certain program behaviors."*

**Variações importantes:**

- **Static vs Dynamic typing.** Em static (Java, TypeScript, Rust), os tipos são verificados *antes* do programa rodar — o compilador rejeita se houver erro. Em dynamic (Python, JavaScript), os tipos só são verificados quando a linha realmente executa. O Epi é static no que é deterministico (tipos rígidos verificados no parse) e dynamic no boundary (tipos epistemicos validados em runtime via Zod, porque o output do LLM é desconhecido até a chamada).

- **Strong vs Weak typing.** Tipos fortes não fazem conversão silenciosa entre tipos distintos. Tipos fracos sim. (`1 + "a"` em JS é tipagem fraca.)

- **Sound type system.** Um sistema de tipos é "sound" se, sempre que ele aceita um programa, esse programa não vai apresentar o tipo de erro que o sistema promete prevenir. *Soundness* é uma propriedade matemática, geralmente provada formalmente em Coq ou Agda. **O Epi v0.3 NÃO tem soundness proof formal — temos a propriedade descrita informalmente, mas não mecanizada.** Esse é o ponto que o Peer Reviewer apontou na revisão (W2).

### 1.2 Linguagem de domínio específico (DSL)

**[CONCEITO]** Uma **DSL** é uma linguagem desenhada para um problema estreito. Contrasta com **linguagem de propósito geral** (Python, Java).

Dois tipos:

- **DSL externa:** tem sua própria sintaxe, parser, etc. Exemplos: SQL, HTML, regex, Prisma schema. **O Epi é uma DSL externa** — tem grammar EBNF própria, parser Lark.
- **DSL interna (embedded):** vive dentro de uma linguagem hospedeira. Exemplos: Ruby DSLs como RSpec, builder patterns em Kotlin. Você "constrói" a DSL usando construções da linguagem mãe.

**Por que DSL externa para o Epi?** Porque queremos que a separação Rigid/Epistêmica seja **sintaticamente óbvia** — o leitor humano vê `AI.Enum(...)` e sabe imediatamente que está em terreno estocástico. Numa DSL embedded em TypeScript, isso ficaria misturado com o resto do código TS.

### 1.3 Compilador, transpilador, interpretador

**[CONCEITO]** Três formas de "executar" um programa de linguagem A:

- **Compilador:** traduz A para uma linguagem de baixo nível (assembly, bytecode). Ex.: GCC, javac.
- **Interpretador:** executa A diretamente, expressão por expressão. Ex.: CPython (na maior parte), node (com JIT).
- **Transpilador (source-to-source compiler):** traduz A para outra linguagem de **alto nível**. Ex.: TypeScript → JavaScript, Babel, Sass → CSS. **O Epi é um transpilador**: `.epi` → projeto TypeScript/Next.js.

A diferença prática: o output do Epi é código TypeScript humanamente legível, que você pode abrir, editar (ainda que não devesse), e debugar com ferramentas TypeScript existentes (VS Code, prettier, etc.).

### 1.4 Grammar e EBNF

**[CONCEITO]** Uma **gramática formal** é um conjunto finito de regras que descreve exatamente quais sequências de caracteres pertencem a uma linguagem. Sem grammar, você não pode escrever um parser; sem parser, você não pode validar um programa.

**EBNF** (*Extended Backus-Naur Form*) é a notação mais comum para grammars. Lê-se como "esta produção é igual a esta sequência":

```
field_decl ::= IDENT ":" type
type       ::= rigid_type | epistemic_type
rigid_type ::= "UUID" | "Text" | "Int" | ...
```

Significa: um `field_decl` (declaração de campo) é um identificador, seguido de `:`, seguido de um tipo; e tipo é ou um `rigid_type` ou um `epistemic_type`; e `rigid_type` é uma das palavras-chave listadas.

**Lark** é uma biblioteca Python que aceita EBNF e produz um parser. O Epi usa Lark para parsear `.epi` em uma árvore.

### 1.5 AST (Abstract Syntax Tree)

**[CONCEITO]** Quando o parser termina, o output não é texto — é uma **árvore sintática abstrata**: uma estrutura de dados onde cada nó é uma construção da linguagem.

Exemplo: o parser do Epi recebe:

```epi
Entity Submissao {
    id: UUID(auto),
    avaliacao: AI.Enum(Correto, Parcial, Incorreto)
}
```

E produz um objeto Python (`Pydantic`) com a estrutura:

```python
EpiProgram(
    entities=[
        Entity(
            name="Submissao",
            fields=[
                Field(name="id", type=RigidType("UUID", modifiers=["auto"])),
                Field(name="avaliacao",
                      type=EpistemicType(kind="Enum",
                                         enum_values=["Correto","Parcial","Incorreto"])),
            ]
        )
    ],
    guards=[], pulses=[], pipelines=[], lenses=[]
)
```

Esse objeto é o que os geradores (Layer 2 e Layer 3) consomem. **Sem AST, não há transpilador.**

### 1.6 Information-Flow Control (IFC)

**[CONCEITO]** **IFC** é uma família de técnicas que rastreiam, no sistema de tipos, **de onde um valor veio**, não só *o que ele é*. Ex.: um campo marcado como "secret" não pode ser concatenado em um log "public" — o sistema rejeita.

A referência canônica para o Epi é **Russo & Sabelfeld, CSF 2010** (*Dynamic vs. Static Flow-Sensitive Security Analysis*), que o Prof. Fernando Magno sugeriu. O que esse paper faz: separa staticamente o tratamento de valores "high" (secret) e "low" (public), e prova **non-interference** — que valores high não influenciam valores low de forma indevida.

**A analogia com Epi:** em vez de níveis de confidencialidade (high/low), o Epi rastreia **provenance epistêmica** — se o valor veio de código determinístico (Rigid) ou de LLM (Epistemic). E em vez de prevenir flow de "high para low", o Epi previne que valores epistêmicos cheguem à persistência sem passarem por um validador.

A propriedade que afirmamos informalmente no paper é:

> *Para todo programa Epi bem-tipado, todo caminho de uma expressão `AI.*`-tipada até um sumidouro de persistência (DB write) no código gerado passa por um validador daquele tipo.*

Isso é estruturalmente análogo à non-interference do IFC, com "tipo epistêmico" no lugar de "nível de segurança". **Não temos prova formal disso ainda** — temos o transpilador que constrói esse caminho, e podemos inspecionar o código gerado para verificar empiricamente.

### 1.7 Compile-time vs Runtime

**[CONCEITO]** Duas fases na vida de um programa:

- **Compile-time:** quando o compilador/transpilador está lendo o código fonte. Ainda não há valores reais.
- **Runtime:** quando o programa está rodando com dados reais.

No Epi:

- O **parser e os geradores rodam em compile-time.** Eles produzem o projeto TypeScript.
- Os **validadores Zod, os checkpoints, e as chamadas LLM rodam em runtime**, quando uma requisição HTTP chega ao app gerado.

A frase "by construction" que aparece muito no paper significa: a propriedade é garantida em compile-time pelo fato do código gerado ter certa estrutura, não por uma verificação que acontece em runtime.

---

## 2. O que é o Epi

Em uma frase: **Epi é uma DSL externa cujo transpilador gera, a partir de uma especificação declarativa de alto nível, um projeto Next.js completo onde a validação de saída de LLMs é estruturalmente inevitável.**

Decompondo:

- **DSL externa**: linguagem com sintaxe própria (`.epi`), parser próprio (Lark+EBNF).
- **Transpilador**: traduz `.epi` para um projeto Next.js+TypeScript+Prisma+Zod.
- **Especificação declarativa de alto nível**: você diz **o que** quer (entidades, regras de autorização, classificações por IA), não **como** implementar.
- **Validação estruturalmente inevitável**: o código gerado não tem um caminho de execução que persiste o resultado de uma chamada LLM sem antes passar pelo validador Zod do tipo declarado.

A última parte é o ponto. Sem Epi, validação de output de LLM é uma decisão *opcional* do desenvolvedor — se ele esquecer, valor alucinado entra no banco. Com Epi, validação é **emitida pelo transpilador**: para omitir, você precisaria editar o output, e a próxima `epi transpile` reescreveria.

### 2.1 Os cinco primitivos

A linguagem tem cinco construtores top-level:

| Primitivo | O que declara | Análogo em outras linguagens |
|---|---|---|
| **Entity** | Schema de dados com campos rígidos e epistêmicos | Prisma model, SQL CREATE TABLE, dataclass |
| **Guard** | Predicado de autorização | Middleware de auth, RBAC rule |
| **Pulse** | Unidade de execução de IA com prompt, temperatura, fallback | Function que chama LLM (mas tipada) |
| **Pipeline** | Composição de Pulses com política de erro | Workflow, DAG |
| **Lens** | Descritor de UI semântico | View, page component |

Só dois invocam o LLM: **Pulse** (sempre) e os campos com tipo `AI.*` dentro de **Entity** (indiretamente, quando algum Pulse retorna para aquele campo). Os outros três são 100% determinísticos.

### 2.2 O fluxo conceitual

Um exemplo educacional ilustra:

```epi
Entity Submissao {
    id: UUID(auto),
    resposta_aluno: Text,
    avaliacao: AI.Enum(Correto, Parcial, Incorreto, confidence_threshold: 0.85)
}

Guard SoProfessores {
    Condition: Auth.Role == "Professor"
}

Pulse AvaliarResposta {
    Input: Submissao
    Protect: Guard.SoProfessores
    Process: Execute: AI.classify(
        source: Input.resposta_aluno,
        prompt: file("@prompts/avaliar.md"),
        on_low_confidence: Checkpoint.ReviewRequired(role: "Professor")
    )
    Output: Submissao.avaliacao
}

Pipeline FluxoAvaliacao { Flow: AvaliarResposta }
```

O que o transpilador faz com isso:

1. **Parser** (Layer 1) constrói o AST.
2. **Rigid Generator** (Layer 2) emite:
   - `prisma/schema.prisma` com a tabela `Submissao` (incluindo coluna `avaliacao String` com anotação `@epi:epistemic`)
   - `middleware/so-professores.ts` com a checagem `session.role === "Professor"`
   - `validators/submissao.ts` com `z.enum(["Correto","Parcial","Incorreto"])`
   - `app/api/fluxo-avaliacao/route.ts` que chama o Pulse com o guard antes
3. **Epistemic Generator** (Layer 3) emite:
   - `pulses/avaliar-resposta.ts` que invoca `llmCall(...)`, parseia o JSON de retorno, extrai `_confidence`, e dispatcha para o validador OU para o checkpoint
   - `lib/llm-client.ts` (provider-agnostic, Anthropic ou Ollama)
4. **Scaffold** emite `package.json`, `.env.example`, `next.config.js`, `README.md`.

A garantia: **não há caminho no código gerado em que a string retornada pelo LLM chegue ao Prisma sem antes passar pelo `z.enum(...).safeParse(...)`.** Você pode auditar isso lendo `pulses/avaliar-resposta.ts`.

---

## 3. O sistema de tipos epistêmico

A contribuição central. Esta é a seção que mais importa para defender o paper.

### 3.1 Dois domínios

Todo valor em Epi pertence a um de dois domínios:

**Rigid (determinístico, sem IA):**
```
UUID  Text  Int  Float  Decimal  Bool  DateTime  JSON
```

Esses são tipos "normais" — análogos a colunas de banco ou tipos de TypeScript. Não têm nada a ver com LLM.

**Epistêmico (inferido por IA, validado no boundary):**
```
AI.Enum(values..., strict, prior, confidence_threshold)
AI.Text(max_tokens)
AI.Classification(labels)
AI.Score(min, max)
AI.Embedding(dimensions)
```

Cada construtor epistêmico carrega **parâmetros obrigatórios** que descrevem **o contrato**:

- `AI.Enum(Alto, Medio, Baixo)`: o LLM tem que retornar uma dessas três strings, mais nada.
- `AI.Score(min: 0, max: 1)`: o LLM tem que retornar um número nesse intervalo.
- `AI.Text(max_tokens: 200)`: o LLM tem que retornar texto até 200 tokens.

E carregam parâmetros **opcionais cross-cutting**:

- `strict: true`: rejeitar valores que não casem exatamente; sem `strict`, há tentativa de coerção.
- `prior: Distribution(...)`: distribuição a priori para Bayesian update (ver seção 7).
- `confidence_threshold: 0.85`: se a confiança auto-reportada do LLM ficar abaixo disso, dispara checkpoint.

### 3.2 O contrato de boundary

Quando você declara um campo `risco: AI.Enum(Alto, Medio, Baixo, strict: true, confidence_threshold: 0.85)`, isso compromete o transpilador a emitir, no código gerado, **quatro artefatos obrigatórios**:

1. **Coluna de banco** (`risco String` no Prisma, com anotação `@epi:epistemic`).
2. **Validador de runtime** (`z.enum(["Alto","Medio","Baixo"])` em Zod).
3. **Chamada LLM tipada** que requer JSON com o campo `_confidence` em `[0,1]`.
4. **Dispatch confidence-aware**: se `_confidence < 0.85`, route para checkpoint; senão, passa pelo Zod.

Esse conjunto é **estrutural**, não opcional. O autor do `.epi` não escolhe se quer cada um dos quatro — eles são consequência da declaração.

### 3.3 A diferença em relação a BAML/DSPy

Esta é a frase de defesa contra a crítica mais comum:

> Frameworks como BAML e DSPy fornecem **artifact (3)** — uma chamada LLM tipada, que valida o output contra um schema. Eles param aí. **Epi adicionalmente gera artifacts (1), (2), e (4)** como consequências estruturais do mesmo tipo. Você não escreve a coluna de banco, não escreve o Zod schema, não escreve o checkpoint route. O tipo carrega a obrigação; o transpilador descarrega.

Em outras palavras: BAML/DSPy resolvem "como chamar o LLM com type safety". Epi resolve "como construir o boundary entre LLM e persistência, de forma que esquecer parte dele seja sintaticamente impossível".

### 3.4 O invariante informal

A propriedade que afirmamos manter (sem prova formal ainda):

> *Para todo programa Epi bem-tipado, todo caminho de execução no código gerado, de uma expressão `AI.*`-tipada até um sumidouro de persistência (`prisma.X.create`, `prisma.X.update`, etc.), passa por um validador (Zod schema) compatível com o tipo declarado.*

Como verificamos isso hoje, sem Coq/Agda:

- **Inspeção de código gerado**: você pode `grep` por `prisma\.` no output e checar manualmente que cada uso é precedido por validação.
- **Testes**: a suite de testes do transpilador (127 unit tests) garante que cada caminho conhecido emite o validador.
- **Demonstração**: o exemplo do paper exercita esse caminho e mostra que funciona.

**Future work** (escrito no paper como "informal"): traduzir esse invariante para uma forma de **typing judgment** em Coq ou Agda e provar mecanicamente.

---

## 4. A arquitetura do transpilador

### 4.1 Três camadas

```
.epi source
   │
   ▼
[Layer 1: Parser]                 100% determinístico
   │   Lark + EBNF → AST Pydantic
   ▼
[Layer 2: Rigid Generator]        100% determinístico
   │   AST → Prisma schema, middleware,
   │         routes, Zod validators, scaffold
   ▼
[Layer 3: Epistemic Generator]    Constrangido pelo Layer 2
       AST → Pulses, Traces, Checkpoint, llm-client
```

A separação é estrutural: o LLM **não roda em Layer 1 ou Layer 2**. Layer 2 emite o contrato (o validador Zod); Layer 3 emite o código que **opera dentro daquele contrato** (a chamada LLM, sempre com `.safeParse()` no output).

**Analogia**: pense em uma fábrica onde a Layer 2 monta a estrutura de aço e os limitadores de segurança, e a Layer 3 instala o motor LLM. O motor não pode girar fora dos limitadores porque eles foram instalados primeiro.

### 4.2 Por que isso importa para o paper

Reviewer de PL vai perguntar: "Por que essa arquitetura, e não monolítica?"

A resposta: separar o gerador determinístico do epistêmico **decouples** duas preocupações distintas. Layer 2 é puramente uma transformação AST → código TypeScript estático; nunca depende do LLM. Se você trocasse o provider de LLM, só Layer 3 e o `llm-client.ts` mudariam — Layer 2 fica intacta. Essa é a base do provider-agnosticism.

Mais importante: **a separação reflete a tese**. A tese diz que o boundary tem que ser construído pelo lado determinístico, não pelo lado estocástico. Se Layer 2 e Layer 3 fossem misturadas, o argumento estrutural ruiria.

### 4.3 Provider-agnostic LLM client

`lib/llm-client.ts` é o único arquivo no projeto gerado que importa SDK de LLM. Ele expõe:

```typescript
interface LLMCallParams {
  systemPrompt: string;
  userContent: string;
  maxTokens: number;
  temperature: number;
}

export async function llmCall(params: LLMCallParams): Promise<{text: string}>;
```

Internamente, baseado em variáveis de ambiente, ele instancia:

- `Anthropic` (do SDK `@anthropic-ai/sdk`) se `EPI_AI_PROVIDER=anthropic`
- `OpenAI` (do SDK `openai`) com `baseURL` customizado se `EPI_AI_PROVIDER=ollama`

A chamada para Ollama funciona porque Ollama implementa a API **OpenAI-compatible** em `http://localhost:11434/v1` — então o mesmo SDK `openai` do JavaScript fala com Ollama sem mudanças.

**Por que isso é interessante para o paper**: o mesmo `.epi` compilado roda contra Claude Sonnet 4 (cloud) e Qwen 2.5 3B (laptop, 1.9 GB) **sem mudar uma linha de código**. Só muda o `.env`. Isso é evidência empírica de provider-agnosticism.

---

## 5. O que o transpilador gera

Para o exemplo `avaliacao-simples.epi` (30 linhas), o output é **13 arquivos**, aproximadamente **700 linhas de TypeScript + Prisma schema**.

| Arquivo gerado | O que é | Quem emite |
|---|---|---|
| `prisma/schema.prisma` | Schema do banco | Layer 2 (`prisma.py`) |
| `middleware/so-professores.ts` | Guard de autenticação | Layer 2 (`middleware.py`) |
| `app/api/fluxo-avaliacao/route.ts` | Route handler do Pipeline | Layer 2 (`routes.py`) |
| `validators/submissao.ts` | Zod schemas + Bayesian update | Layer 2 (`validators.py`) |
| `pulses/avaliar-resposta.ts` | Função Pulse com LLM call | Layer 3 (`ai_scan.py`) |
| `lib/llm-client.ts` | Adapter provider-agnostic | Layer 3 (`scaffold.py`) |
| `package.json` | Dependências npm | Scaffold |
| `tsconfig.json` | Config TypeScript | Scaffold |
| `next.config.js` | Config Next.js | Scaffold |
| `.env.example` | Template de env vars | Scaffold |
| `.gitignore` | Padrão Next.js | Scaffold |
| `README.md` | Quickstart do projeto gerado | Scaffold |
| `prompts/avaliar_simples.md` | Prompt referenciado | Copiado de `prompts/` |

Quando o usuário roda `npm install && npx prisma migrate dev && npm run dev`, ele tem uma aplicação web rodando com:

- Endpoint POST que aceita uma `Submissao`
- Verifica que o usuário é Professor (Guard)
- Chama o LLM (via Ollama ou Anthropic, conforme `.env`)
- Parseia o JSON, extrai `_confidence`
- Se confidence baixa → retorna `{_epi_checkpoint: true, ...}` (Checkpoint)
- Se confidence ok → valida com Zod, persiste no banco

Tudo isso vem do mesmo `.epi` de 30 linhas.

---

## 6. Trace + Checkpoint

Esta é a contribuição conceitual da **Profa. Rosa Maria Vicari** (sua coorientadora). Materializada no v0.3.

### 6.1 O problema

Em uma avaliação pedagógica feita por IA, o professor não quer saber **só** a classificação final ("Correto", "Parcial", "Incorreto"). Ele quer **inspecionar o raciocínio** — o que a IA interpretou da pergunta, quais critérios usou, antes de a classificação ser registrada.

Sem Epi, isso é algo que o dev tem que escrever à mão: um endpoint extra de "inspeção", um sistema de paused/resumed, um audit trail. Geralmente é esquecido em sistemas que poderiam se beneficiar dele.

### 6.2 A construção do Epi

Um `Pulse` pode ser decomposto em uma sequência de **Trace** steps. Cada Trace:

- **Executa** uma chamada LLM com prompt e parâmetros próprios.
- **Expõe** campos específicos do raciocínio intermediário (`Expose: interpretacao, criterios`).
- Pode **pausar em um Checkpoint** para revisão humana antes do próximo Trace.

Exemplo:

```epi
Pulse AvaliarResposta {
    Trace InterpretarEnunciado {
        Execute: AI.reason(source: Input.enunciado, prompt: file("@prompts/compreender.md"))
        Expose: interpretacao, conceitos_chave, criterios
        Checkpoint: ReviewRequired(role: "Professor")
    }
    Trace ClassificarResposta {
        Execute: AI.classify(
            source: Input.resposta_aluno,
            prompt: file("@prompts/avaliar.md"),
            confidence_threshold: 0.85,
            on_low_confidence: Checkpoint.ReviewRequired(role: "Professor")
        )
    }
}
```

O transpilador emite:

- Um **store de TraceState** (`lib/trace-store.ts`) em memória que rastreia traces ativos.
- **Rotas HTTP de inspect/resume** (`app/api/traces/.../[traceId]/inspect/route.ts` e `.../resume/route.ts`): o professor pode consultar o estado de um trace pausado e aprovar/corrigir o raciocínio.
- **Audit trail**: cada decisão humana é registrada com timestamp e usuário.

### 6.3 Por que isso importa academicamente

Mecanismos de "human-in-the-loop" são comuns em sistemas de produção, mas raramente são **primeira classe na linguagem**. Em Epi, `Trace + Checkpoint` é uma construção sintática que o transpilador entende e materializa. Se você usa o construto, você tem o audit trail automático; se você não usa, não tem. **Não há código defensivo a esquecer.**

Em uma analogia: é como `try/finally` em linguagens com tratamento de exceção — você não precisa lembrar de fechar o arquivo, a linguagem garante.

---

## 7. Computação estocástica

Esta é a contribuição do **Prof. Dante Barone**.

### 7.1 O conceito de prior

Modelos de IA produzem outputs com algum grau de incerteza. Sozinhos, eles fazem uma "leitura crua" do input. Mas em muitos domínios você tem **conhecimento prévio sobre a distribuição esperada**.

Exemplo concreto, do paper: numa turma típica de avaliação pedagógica, historicamente:
- 40% das respostas são Corretas
- 45% são Parciais
- 15% são Incorretas

Isso é a **distribuição a priori**. Codificado em Epi:

```epi
avaliacao: AI.Enum(
    Correto, Parcial, Incorreto,
    prior: Distribution(Correto: 0.40, Parcial: 0.45, Incorreto: 0.15)
)
```

### 7.2 Atualização bayesiana

Quando o LLM faz uma classificação, ele reporta uma "likelihood" — qual a probabilidade dele estar certo para cada classe. Por exemplo, ele pode dizer:
```
{"avaliacao":"Correto", "_confidence":0.7,
 "likelihoods":{"Correto":0.7,"Parcial":0.2,"Incorreto":0.1}}
```

A **regra de Bayes** combina o prior (conhecimento de domínio) com a likelihood (output do modelo) para produzir a **posterior** — a estimativa atualizada:

```
P(classe | evidência) ∝ P(evidência | classe) × P(classe)
posterior              ∝ likelihood          × prior
```

Isso é normalizado para somar 1, e a classe mais provável é selecionada com sua confiança.

O transpilador emite, em `validators/submissao.ts`, uma função `bayesianUpdateSubmissaoAvaliacao(likelihood)` que faz exatamente isso. Ela retorna:

```typescript
{ prediction: "Correto",
  confidence: 0.78,
  posterior: { Correto: 0.78, Parcial: 0.18, Incorreto: 0.04 },
  requiresReview: false }
```

### 7.3 Por que isso é interessante

Sem o prior, um modelo pequeno (como Qwen 3B) que "acha" 50/50 entre Correto e Parcial vai escolher arbitrariamente. Com o prior, ele é influenciado pela base rate histórica — o que reduz erros sistemáticos em domínios onde a distribuição é estável.

**Limitação honesta**: o prior é estático, declarado no `.epi`. Não atualiza dinamicamente conforme novos dados chegam. Atualização dinâmica do prior é tema de pesquisa em ML; está fora do escopo do Epi v0.3.

---

## 8. O que o Epi NÃO faz

A lista honesta. Se alguém perguntar "o Epi resolve X?", se X estiver aqui, a resposta é **não**.

### 8.1 Não previne alucinação

Esta é a frase mais importante de todo o paper. Repito porque é fácil cair na armadilha:

> **Epi não previne alucinação.** Ele *contém* alucinação — impede que um output alucinado se propague para a persistência sem passar por validação. O LLM ainda pode (e vai) alucinar.

Se alguém disser "o Epi resolve alucinação de LLM", essa pessoa entendeu mal. A frase exata da tese, decorada:

> *LLM hallucination cannot be prevented, but it can be contained — by construction, at a type-system boundary in generated code.*

### 8.2 Não é um framework de agentes

LangChain, LangGraph, AutoGPT, CrewAI — esses são frameworks para construir agentes que tomam decisões iterativas, usam tools, planejam. O Epi não faz isso.

O escopo do Epi é **decisão-grade single-turn**: um Pulse recebe um input, classifica/extrai/gera uma resposta tipada, persiste com validação. Não há loop de raciocínio, não há tool use, não há agente.

Se você precisa de agente, use LangGraph. Se você precisa de validar uma classificação por LLM antes de gravar no banco, use Epi.

### 8.3 Não é um prompt optimizer

DSPy (Stanford) é um framework que **otimiza prompts**: você descreve o objetivo, ele iterativamente refina o prompt para melhorar acurácia. O Epi não faz isso. Os prompts em Epi são arquivos `.md` escritos à mão, referenciados pelo `.epi`.

São objetivos ortogonais. **DSPy + Epi seria uma combinação possível** — você usa DSPy para otimizar o prompt, depois cola o prompt otimizado no arquivo `.md` que o Pulse referencia.

### 8.4 Não é um chatbot framework

Chat conversacional não cabe no modelo. Não há sessão de conversa, não há contexto multi-turn, não há streaming. O Epi assume **interações discretas**: input chega, output tipado é produzido, persiste.

Para chatbot, use Vercel AI SDK, Chat SDK, ou similar.

### 8.5 Não tem formalização mecanizada

Repetindo da seção 1.1: **não temos prova formal em Coq/Agda** do invariante de non-interference. Temos a propriedade descrita informalmente e o transpilador construído para satisfazê-la.

Para venue PL forte (PLDI, POPL), isso seria um bloqueio. Para SBLP short paper / PLATEAU / Onward!, é aceitável como "future work explicitamente declarado".

### 8.6 Lens.Mood é fraco

`Lens.Mood: "Clean, Educational, Trustworthy"` mapeia palavras-chave para classes Tailwind via lookup table determinística. **Não é geração de UI por LLM.** O paper declara isso como experimental.

A razão da existência: queríamos um "boundary epistêmico" também na UI (UI gerada por LLM seria mais um caso epistêmico). Mas a implementação atual é lookup, não LLM. Por coerência com a tese, vamos provavelmente remover ou tipar formalmente em v0.4.

### 8.7 FastAPI target está bloqueado no CLI

O transpilador atualmente só emite Next.js completo. Tem um target FastAPI parcialmente implementado, mas ele gera artefatos inconsistentes (mistura `.ts` e `.py`), então está intencionalmente bloqueado no CLI com mensagem honesta.

### 8.8 Não há estudo empírico controlado ainda

O paper apresenta **um cenário (educação) com três respostas**, contra dois modelos LLM. Isso é "worked example", não "controlled study". Comparação contra baselines hand-written (em termos de LoC, audit coverage, developer time) está em "Future Work".

---

## 9. Decisões de design

Quando alguém perguntar "por que vocês fizeram X em vez de Y?", aqui estão as razões.

### 9.1 Por que linguagem nova em vez de biblioteca?

**Defesa**: porque a separação Rigid/Epistêmica precisa ser *sintaticamente óbvia* e *verificada no parse*, não numa convenção opcional. Em uma biblioteca TypeScript (ex.: `epi.enum("Alto","Medio","Baixo")`), o dev pode esquecer de chamar; em uma DSL externa com tipos, o parser **rejeita** programas mal-formados antes do gerador rodar.

**Contraargumento honesto**: uma DSL embedded com builders forçaria type-check via TypeScript ("se você não declarar `.confidenceThreshold(0.85)`, o tipo do builder não está completo"). Isso resolveria boa parte do problema sem DSL externa.

A escolha de DSL externa também é por **legibilidade humana**: um `.epi` de 30 linhas é mais legível do que 30 chamadas de builder TypeScript encadeadas. Para um produto/projeto educacional onde stakeholders não-técnicos podem olhar o source (professor, advogado, médico), isso é uma vantagem.

### 9.2 Por que Next.js como target?

**Razões pragmáticas**:
- Stack moderno e estável (React + Node + TypeScript)
- Prisma como ORM tem suporte excelente
- Vercel facilita deploy sem precisar gerenciar infra
- Zod é first-class no ecossistema TypeScript

**O que rejeitamos**:
- Remix: similar mas com menos massa crítica de adoção
- Express puro: muito código boilerplate
- Django/FastAPI: alvo Python, mas o stack Python tem menos coerência (validators? Pydantic. UI? não tem; SSR? Jinja). Em Next.js, todo o stack converge.

### 9.3 Por que Zod e não outros?

- TypeScript-first (inferência de tipos)
- API simples (`z.enum(...)`, `z.object(...)`, `.safeParse()`)
- `safeParse` retorna union discriminada (`success: true` ou `success: false`), facilitando dispatch
- Suporta JSON schemas complexos sem precisar gerar arquivos JSON Schema separados

Alternativas (io-ts, runtypes, valibot) servem, mas Zod tem mindshare maior.

### 9.4 Por que Lark e não outro parser?

- Python-native (o transpilador é em Python)
- EBNF amigável (sintaxe próxima do padrão)
- Performance suficiente para arquivos `.epi` pequenos
- Documentação razoável

Alternativas: ANTLR (mais robusto mas tooling pesado), PLY (mais antigo), Tree-sitter (excelente mas C/wrapper).

### 9.5 Por que SQLite como default no quickstart?

- Zero setup — file-based, não precisa de servidor de banco
- Prisma suporta nativamente
- Para um demo de 30 segundos, instalar PostgreSQL é fricção desnecessária

Trade-off: SQLite não escala horizontalmente. Para produção, troca para PostgreSQL editando uma linha no `schema.prisma`. Para demo/POC/Loom da Rosa, SQLite é suficiente.

### 9.6 Por que Python para o transpilador?

- Você é mais produtivo em Python
- Lark, Pydantic, Typer são bons o suficiente
- Não há requisito de performance crítica (transpilação leva ~1s)
- PyPI distribution é familiar para a comunidade acadêmica

### 9.7 Por que Apache 2.0 como licença?

- Permissiva (pode ser usado comercialmente)
- Compatible com a maioria das outras licenses
- Inclui cláusula de patente expressa (proteção a contribuidores)
- Padrão em projetos acadêmicos abertos

GPL teria limitado adoção comercial. MIT é mais permissivo mas sem proteção de patente.

---

## 10. Como argumentar

Cada subseção é uma crítica provável + resposta calibrada.

### 10.1 "Mas isso é só um wrapper de Zod"

**Resposta**: Zod valida outputs em runtime. Epi *gera* os Zod schemas a partir de tipos em compile-time, junto com a coluna de banco, a chamada LLM, o checkpoint route, e o audit trail. **Os 4 artefatos saem da mesma declaração.** Você não escolhe se quer cada um deles. É a obrigação que o tipo carrega.

Se fosse "só um wrapper de Zod", seria possível omitir o checkpoint, omitir o threshold. Em Epi, não é — porque o tipo força.

### 10.2 "Por que não usar BAML?"

**Resposta**: BAML é excelente para tipar chamadas LLM individuais. Epi não compete com BAML — opera em escopo mais amplo. BAML gera artifact (3) do contrato; Epi adicionalmente gera (1), (2), e (4). Você pode até imaginar Epi *usando* BAML internamente para a parte (3) — não fazemos isso hoje, mas seria razoável.

Diferença essencial: BAML deixa as outras partes (schema, validação no DB write, checkpoint, audit) como responsabilidade do dev. Epi torna isso estrutural.

### 10.3 "Por que não usar DSPy?"

**Resposta**: DSPy otimiza prompts. Epi não otimiza prompts. Objetivos ortogonais — podem coexistir. Você usa DSPy para descobrir o melhor prompt para uma classificação, depois cola o prompt em um arquivo `.md` que o Pulse referencia.

### 10.4 "LLM hallucination não é resolvido — vocês admitem isso"

**Resposta**: correto, e essa é exatamente a honestidade central do trabalho. Não pretendemos resolver alucinação. Pretendemos *contê-la no boundary*. Pesquisas que prometem resolver alucinação são geralmente exageradas. Pesquisa que mostra como tornar alucinação **não propagável** sem esforço extra do dev é honesta e útil.

### 10.5 "Por que não validar tudo manualmente em TypeScript?"

**Resposta**: porque o problema P3 do paper é exatamente esse — *validação manual é opcional e frequentemente esquecida*. Em produção, vimos esse padrão repetir. Quando a validação é obrigatória por geração, não é esquecida.

Há um custo: o dev tem que aprender uma DSL nova. Mas para uma equipe ou pesquisador num domínio onde isso é estrutural (educação, jurídico, saúde), o custo é justificável.

### 10.6 "Como vocês sabem que o transpilador é correto?"

**Resposta**: hoje, via testes (127 unit tests) e inspeção manual do código gerado. Não temos prova formal de soundness. Isso está explícito no paper como "future work: mechanized formalization".

Se a pessoa for um teórico tipo PLDI, ela vai querer Coq. Concorde — diga que sim, está nas próximas etapas. Não defenda como se já tivesse.

### 10.7 "Por que SBLP e não PLDI/POPL/Onward!?"

**Resposta**: porque o trabalho está em fase early-stage. PLDI/POPL exigem formalização completa. PLATEAU/Onward! são opções viáveis para versão estendida. SBLP é venue brasileiro de PL com peer review real e prazo razoável para a etapa atual. Submeter ao SBLP agora estabelece prioridade e nos dá feedback antes de mirar venues maiores.

### 10.8 "Vocês têm um único cenário de avaliação. Isso é fraco."

**Resposta**: correto. É um worked example, não uma evaluation controlada. **Reframe explícito** no paper (Seção 5, "Demonstration"). O Peer Reviewer apontou isso (W1) e revisamos o framing para refletir. Estudo controlado contra baseline hand-written é Future Work.

---

## 11. Glossário

Termos técnicos que aparecem ao longo do manual e do paper.

| Termo | Definição curta |
|---|---|
| **AST** | Abstract Syntax Tree — árvore produzida pelo parser, consumida pelos geradores |
| **By construction** | Garantia obtida por como o código é gerado, não por checagem runtime |
| **Compile time** | Fase em que o transpilador roda; antes de qualquer dado real |
| **Containment (epistêmica)** | Impedir que um valor de origem estocástica chegue à persistência sem validação |
| **DSL** | Domain-Specific Language; linguagem para um problema estreito |
| **EBNF** | Extended Backus-Naur Form; notação padrão para gramáticas formais |
| **Epistêmico** | Em Epi: domínio de valores inferidos por LLM (vs. Rigid) |
| **Fail closed** | Sistema falha negando acesso/operação por padrão (vs. fail open) |
| **IFC** | Information-Flow Control; disciplina de tipos para rastrear origem de valores |
| **Non-interference** | Propriedade que valores de um domínio não influenciam outro indevidamente |
| **Pulse** | Em Epi: unidade declarativa de execução LLM com input/output tipados |
| **Posterior** | Distribuição de probabilidade após atualização bayesiana com nova evidência |
| **Prior** | Distribuição de probabilidade inicial baseada em conhecimento de domínio |
| **Rigid (em Epi)** | Domínio determinístico, sem envolvimento de LLM |
| **Runtime** | Fase em que o código gerado executa com dados reais |
| **Soundness** | Propriedade formal: se o sistema aceita o programa, ele não exibe certo erro |
| **Static typing** | Tipos verificados antes da execução |
| **Transpiler** | Compilador source-to-source (de linguagem alta para linguagem alta) |
| **Type judgment** | Notação formal `Γ ⊢ e : τ` ("no contexto Γ, expressão e tem tipo τ") |
| **Worked example** | Demonstração concreta de mecanismo, não estudo controlado |
| **Zod** | Biblioteca TypeScript de schema validation em runtime |

---

## 12. Apêndice

### 12.1 Referências essenciais para aprofundar

**Para sistema de tipos:**
- **Pierce, B. C.** *Types and Programming Languages*. MIT Press, 2002. — Livro fundamental. Os primeiros 5 capítulos cobrem o que você precisa. Disponível na biblioteca da UFRGS.

**Para information-flow control:**
- **Russo, A., Sabelfeld, A.** *Dynamic vs. Static Flow-Sensitive Security Analysis*. CSF 2010. — Referência que Fernando indicou. Leia mesmo se for rápido; ancora o Related Work do nosso paper.
- **Sabelfeld, A., Myers, A. C.** *Language-Based Information-Flow Security*. IEEE J. Selected Areas in Communications, 2003. — Survey clássica de IFC. Boa visão geral.

**Para probabilistic programming (Dante):**
- **Baudart, G. et al.** *Reactive Probabilistic Programming with ProbZelus*. PLDI 2020. — Citado no paper.
- **Goodman, N. D., Mansinghka, V. K., et al.** *Church: A language for generative models*. UAI 2008. — PPL clássica.

**Para LLM applications:**
- **Khattab, O. et al.** *DSPy: Compiling Declarative Language Model Calls Into Self-Improving Pipelines*. arXiv:2310.03714, 2023.
- **BAML documentation**. https://github.com/BoundaryML/baml

**Para semântica formal (se quiser fazer a mechanization no Coq):**
- **Pierce, B. C.** *Software Foundations* (volumes online gratuitos). https://softwarefoundations.cis.upenn.edu

### 12.2 Ferramentas mencionadas

| Ferramenta | O que é | Como usamos |
|---|---|---|
| **Lark** | Parser library Python (LALR/Earley) | Layer 1 do transpilador |
| **Pydantic** | Data validation Python | Modelo do AST |
| **Typer** | CLI framework Python | Comandos `epi validate/transpile/init` |
| **Jinja2** | Template engine Python | Geração de strings TypeScript |
| **Prisma** | ORM/schema TypeScript | Modelo de banco no projeto gerado |
| **Zod** | Schema validation TypeScript | Validators no boundary |
| **Next.js** | React framework | Stack alvo do transpiler |
| **Ollama** | LLM runtime local | Provider alternativo |
| **Anthropic SDK** | Cliente Claude | Provider primário |

### 12.3 Comandos que você vai usar frequentemente

```bash
# Validar sintaxe sem gerar nada
epi validate examples/contrato.epi

# Gerar projeto a partir de .epi
epi transpile examples/contrato.epi --target nextjs --outdir ./out

# Bootstrap projeto novo
epi init meu-app

# Ver versão
epi version

# Rodar testes do transpilador
source .venv/bin/activate
python -m pytest --tb=line -q

# Gerar .docx do paper
python paper/gen_docx.py

# Publicar nova versão no PyPI
source .venv/bin/activate
python -m build
twine upload dist/epi_lang-X.Y.Z*
```

### 12.4 Arquivos críticos do projeto (onde mexer quando)

| Arquivo | Mude quando... |
|---|---|
| `epi/grammar/epi.lark` | Quer adicionar/mudar sintaxe da linguagem |
| `epi/parser/ast_nodes.py` | Quer adicionar/mudar tipos no AST |
| `epi/parser/builder.py` | Quer mudar como o parser constrói o AST |
| `epi/generators/deterministic/*.py` | Quer mudar o que Layer 2 emite |
| `epi/generators/epistemic/*.py` | Quer mudar o que Layer 3 emite |
| `epi/generators/scaffold.py` | Quer mudar arquivos de config gerados (package.json etc.) |
| `epi/cli.py` | Quer adicionar comando novo |
| `tests/*.py` | Sempre que mudar geradores |
| `docs/SPEC.md` | Quer atualizar especificação canônica |
| `docs/PAPER.md` | Quer revisar o draft Markdown do paper |
| `paper/main.tex` | Quer revisar a versão LaTeX do paper |

### 12.5 Decisões pendentes e abertas (Tier 4 da revisão)

- Rodar variabilidade do `_confidence` do Qwen em múltiplos runs do mesmo input. Anotar no paper.
- Explicitar se `_confidence` é prompt-elicited ou logprob-computed.
- Especificar ordem de composição `prior + confidence_threshold` no Bayesian update.
- Decidir se Lens.Mood vai virar tipo formal ou ser removido em v0.4.
- Avaliar mechanization em Coq como future work — quem dentro da UFRGS pode coorientar isso?

---

**Fim do manual.**

Quando alguém te perguntar algo sobre o Epi que você não souber responder de cabeça, abra este arquivo, faça `Cmd+F`, e encontre a seção. Foi escrito para isso.
