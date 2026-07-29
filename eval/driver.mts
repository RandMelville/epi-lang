/**
 * Epi containment harness: driver
 *
 * Runs the curated dataset through the *generated* Pulse, unmodified.
 *
 * The point of this file is what it does NOT do: it does not reimplement the
 * epistemic boundary. It imports `avaliarResposta` from the transpiler output
 * and records what that function returned. The threshold check, the Zod
 * validation, the checkpoint route and the manual-review fallback are all
 * executed by generated code. Only the HTTP route and the Prisma write are
 * bypassed, since neither participates in the containment decision.
 *
 * Usage (from inside the generated app directory):
 *   npx tsx epi-eval/driver.mts --dataset epi-eval/dataset.jsonl --out results.jsonl
 *
 * Env: whatever the generated lib/llm-client.ts reads (EPI_AI_PROVIDER,
 * EPI_AI_MODEL, EPI_AI_BASE_URL, ANTHROPIC_API_KEY).
 */

import { readFileSync, appendFileSync, existsSync, unlinkSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import {
  classify,
  extractRawLabel,
  labelInEnum,
  type Outcome,
} from "./boundary.mts";

// ---------------------------------------------------------------------------
// CLI args
// ---------------------------------------------------------------------------

function arg(name: string, fallback?: string): string {
  const i = process.argv.indexOf(`--${name}`);
  if (i !== -1 && process.argv[i + 1]) return process.argv[i + 1];
  if (fallback !== undefined) return fallback;
  throw new Error(`Missing required argument --${name}`);
}

const datasetPath = resolve(arg("dataset", "epi-eval/dataset.jsonl"));
const outPath = resolve(arg("out", "results.jsonl"));
const pulsePath = resolve(arg("pulse", "pulses/avaliar-resposta.ts"));
const limit = Number(arg("limit", "0")) || Infinity;
const repeats = Number(arg("repeats", "1"));
// Which .epi variant this app was transpiled from. Recorded in every row so
// two runs against the same provider cannot be merged by accident.
const variant = arg("variant", "v1-resposta");

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Item {
  id: string;
  categoria: string;
  enunciado: string;
  resposta_aluno: string;
  gabarito: "Correto" | "Parcial" | "Incorreto";
  ambiguo: boolean;
  contencao_obrigatoria: boolean;
  ataque_formato: boolean;
  justificativa: string;
}

// ---------------------------------------------------------------------------
// Run
// ---------------------------------------------------------------------------

const items: Item[] = readFileSync(datasetPath, "utf-8")
  .split("\n")
  .map((l) => l.trim())
  .filter((l) => l.length > 0)
  .map((l) => JSON.parse(l) as Item);

if (items.length === 0) throw new Error(`Empty dataset: ${datasetPath}`);

const pulseMod: any = await import(pathToFileURL(pulsePath).href);
const avaliarResposta = pulseMod.avaliarResposta;
if (typeof avaliarResposta !== "function") {
  throw new Error(
    `${pulsePath} does not export avaliarResposta. Did the transpiler output change?`
  );
}

// Provider identity, read from the generated client so the record cannot
// disagree with what actually ran.
const clientMod: any = await import(
  pathToFileURL(resolve("lib/llm-client.ts")).href
);
const provider = clientMod.epiLLMProvider ?? "unknown";
const model = clientMod.epiLLMModel ?? "unknown";

if (existsSync(outPath)) unlinkSync(outPath);

console.log(`[harness] provider=${provider} model=${model} variant=${variant}`);
console.log(`[harness] ${items.length} items x ${repeats} repeat(s) -> ${outPath}`);

let n = 0;
for (let rep = 1; rep <= repeats; rep++) {
  for (const item of items) {
    if (n >= limit) break;
    n++;

    // The Submissao entity, minus the auto fields. The item id is deliberately
    // left out: variant v2 forwards this whole object to the model, and the
    // dataset id must not become part of the model's input.
    const input = {
      enunciado: item.enunciado,
      resposta_aluno: item.resposta_aluno,
    };

    const t0 = process.hrtime.bigint();
    let result: any;
    let harnessError: string | null = null;
    try {
      result = await avaliarResposta(input as any);
    } catch (e) {
      harnessError = e instanceof Error ? e.message : String(e);
    }
    const latencyMs = Number(process.hrtime.bigint() - t0) / 1e6;

    const outcome: Outcome = harnessError ? "erro_harness" : classify(result);
    const rawLabel = harnessError ? null : extractRawLabel(outcome, result);

    const record = {
      id: item.id,
      repeticao: rep,
      categoria: item.categoria,
      gabarito: item.gabarito,
      ambiguo: item.ambiguo,
      contencao_obrigatoria: item.contencao_obrigatoria,
      ataque_formato: item.ataque_formato,
      provider,
      model,
      variante: variant,
      desfecho: outcome,
      valor_persistido: outcome === "persistido" ? String(result) : null,
      rotulo_bruto: rawLabel,
      rotulo_bruto_no_enum: labelInEnum(rawLabel),
      confianca:
        outcome === "checkpoint" && typeof result?.confidence === "number"
          ? result.confidence
          : null,
      latencia_ms: Math.round(latencyMs),
      erro_harness: harnessError,
      // Kept verbatim for audit: this is the evidence trail for every claim
      // the paper makes about a contained item.
      retorno_bruto: harnessError ? null : JSON.stringify(result).slice(0, 2000),
    };

    appendFileSync(outPath, JSON.stringify(record) + "\n", "utf-8");

    const tag = outcome.padEnd(20);
    console.log(
      `[${String(n).padStart(3)}/${items.length * repeats}] ${item.id.padEnd(4)} ${tag} ` +
        `bruto=${String(rawLabel).padEnd(14)} gab=${item.gabarito.padEnd(9)} ${record.latencia_ms}ms`
    );
  }
}

console.log(`\n[harness] done. ${n} records in ${outPath}`);
console.log(`[harness] next: python3 eval/report.py ${outPath}`);
