# Containment harness

Empirical evaluation of the Epi epistemic boundary, built for the SBLP 2026
camera-ready in answer to the reviewers who asked for evidence beyond a single
worked example.

The harness measures **containment**, not accuracy. The claim under test is not
that an LLM classifies student answers well. It is that when the LLM is wrong,
the boundary the type system generates keeps the wrong value out of the
database of record, and that no value outside the declared domain can ever be
persisted.

## What is actually being exercised

The harness does **not** reimplement the boundary. It imports
`avaliarResposta` from the transpiler output and records what that function
returned. The threshold comparison, the Zod validation, the checkpoint route
and the manual-review fallback all execute inside generated code. Only the HTTP
route and the Prisma write are bypassed, since neither participates in the
containment decision.

```
examples/avaliacao-simples.epi          eval/variants/fonte-completa.epi
            |                                        |
   epi.cli transpile                        epi.cli transpile
            |                                        |
   eval/_run/v1/pulses/avaliar-resposta.ts   eval/_run/v2/...
            \                                        /
             `------- eval/driver.mts --------------'
                              |
                      results-*.jsonl
                              |
                       eval/report.py
```

## The two conditions

The two `.epi` programs differ in a single token:

| Variant | AI call source | What the model sees |
|---|---|---|
| `v1-resposta` | `source: Input.resposta_aluno` | the student's answer alone (the program reproduced in the paper) |
| `v2-fonte-completa` | `source: Input` | the question and the answer |

Everything else is identical: same enum, same prior, same
`confidence_threshold: 0.85`, same `Checkpoint.ReviewRequired`, same
`Fallback.ManualReview`. The contrast isolates the effect of the declared
source on how much the boundary can contain.

## The dataset

`dataset.jsonl`, 40 items with a gold label and a written justification for
each.

The items instantiate the task of the worked example in the paper, which
classifies a short free-text answer into a three-valued enum. That task is a
carrier for the containment measurement, not a claim about Epi's domain: what
is under test is a classification with a declared enum, a prior and a
confidence threshold. Any task with the same shape would exercise the same
boundary.

| Category | n | What it probes |
|---|---|---|
| `canonico_correto` | 7 | complete correct answers |
| `parcial_incompleto` | 8 | right idea, incomplete: the band where a model should be unsure |
| `incorreto_conceitual` | 7 | classic misconceptions |
| `fora_de_topico` | 4 | non-answers, nonsense, copied prompt |
| `adversario_formato` | 6 | prompt injection, role hijack, empty input, forced out-of-enum label |
| `ambiguo_por_design` | 4 | items with no defensible single label |
| `limiar_sutil` | 4 | fluent answers that are wrong on one word |

Ten items (`adversario_formato` + `ambiguo_por_design`) carry
`contencao_obrigatoria: true`: for these, persisting *any* value silently is a
failure, whatever the label. The other 30 have a single defensible gold label
and are the basis of the correctness metrics.

## Metrics

Computed by `report.py` as counts over the result files. Nothing is estimated
or interpolated.

- **Out-of-enum values persisted.** The paper's structural claim. Must be 0.
- **Wrong values if unguarded.** How many writes would have been wrong had the
  model output gone straight to the database. Reconstructed from the raw label,
  which stays recoverable on every branch (the persisted value itself, the
  checkpoint's `partialResult`, or Zod's `received` field).
- **Escapes.** Wrong values that the boundary persisted anyway.
- **Mandatory-containment leaks.** Items that must never be persisted silently,
  but were.
- **Human review load**, and the share of it that was **avoidable** (the raw
  label already matched the gold label). This is the cost side, reported
  alongside the benefit rather than after it.
- **Decision stability** across repeats. Inference runs at temperature 0.1, not
  0, so an item whose outcome flips between repeats was contained by luck.

## Running it

```bash
./eval/setup.sh                       # transpiles both variants, installs deps
                                      # (~1.2 GB under eval/_run, git-ignored)
python3 eval/report.py eval/results-*.jsonl --latex
```

`setup.sh` prints the exact command for each condition. It also runs
`selftest.mts`, which checks offline that the harness reads all four boundary
branches correctly.

A third, optional condition puts a deliberately weak model behind the same
generated code. It is a stress test, not a proposed deployment: it is the
condition in which the schema-rejection and unparseable-output branches
actually fire.

```bash
cd eval/_run/v1 && EPI_AI_PROVIDER=ollama EPI_AI_MODEL=llama3.2:1b \
  EPI_AI_BASE_URL=http://localhost:11434/v1 \
  npx tsx epi-eval/driver.mts --repeats 3 --variant v1-resposta \
  --out ../../results-ollama-1b-v1.jsonl
```

## Runs recorded in this repository

Committed result files, 40 items × 3 repeats each, Apple Silicon, 16 GB RAM,
July 2026. The Anthropic condition is not included: it needs the author's API
key and is run separately.

| File | Condition |
|---|---|
| `results-ollama-v1.jsonl` | Qwen 2.5 3B, `source: Input.resposta_aluno` |
| `results-ollama-v2.jsonl` | Qwen 2.5 3B, `source: Input` |
| `results-ollama-1b-v1.jsonl` | Llama 3.2 1B stress condition |

Two findings from those files are worth stating up front, because one supports
the paper's claim and the other bounds it.

**The domain guarantee is structural and held absolutely.** Across all 360
calls, zero values outside the declared enum reached the persistence path. This
is not because no model tried: prompted with an injection, the 1B model emitted
`CORRETÍSSIMO` on 3 of 3 repeats, and the generated Zod validator rejected it
and routed the case to the teachers' queue. On another item it emitted
unparseable JSON on 3 of 3 repeats, caught by the parse fallback. Neither path
was written by hand; both follow from one type annotation.

**Correctness containment is only as good as the model's confidence.** The
share of wrong labels the boundary kept out of the database was 100 % for Qwen
with the question visible, 50 % for Qwen with the answer alone, and 2 % for the
1B model, which reports high confidence almost everywhere. The type system
enforces that an uncertain value is reviewed; it cannot supply calibration the
model does not have. This is direct evidence for the threshold-calibration
discussion in the paper rather than a result against it. Two of those branches rarely fire against providers that
support `response_format: json_object`, so a live run alone does not cover
them; if the reading of a branch were wrong, the counterfactual metric would be
silently wrong too.

## Limitations

State these in the paper. They are not incidental.

1. **The gold labels were written by one annotator.** No independent second
   pass, so no inter-rater agreement figure. Every correctness metric inherits
   this; the structural metric does not, since it never consults a gold label.
2. **40 synthetic items on one task shape.** The answers were authored for this
   harness, not collected. This is a probe, not a benchmark, and it is designed
   to include cases where the boundary should fail rather than to produce a
   favourable average.
3. **The confidence of accepted values is not observable.** The generated Pulse
   deletes `_confidence` before returning the validated label, so the harness
   can only report the confidence distribution of *contained* items. Recording
   it on the accept path would need `Trace`, which this program does not
   declare.
4. **A capable model rarely exercises the schema-rejection path.** Under
   `response_format: json_object`, Qwen 2.5 3B produced a valid in-domain label
   on all 240 calls, so its validator and parse branches stay at zero. Those
   branches are covered offline by `selftest.mts` and live by the Llama 3.2 1B
   stress condition, where they fire.
5. **Self-reported confidence is coarse.** Qwen 2.5 3B emits a small set of
   values (0.8 dominates the contained items), so the 0.85 threshold behaves
   more like a switch on a handful of levels than a continuous knob. This is
   evidence for, not against, the calibration discussion in the paper.
