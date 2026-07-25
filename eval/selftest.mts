/**
 * Epi containment harness: self-test.
 *
 * Verifies that the harness reads the generated boundary correctly on all four
 * branches, without calling any model. Two of those branches (schema rejection
 * and unparseable output) rarely fire against providers that support
 * `response_format: json_object`, so a live run alone does not cover them. If
 * the reading of a branch were wrong, the counterfactual metric in report.py
 * would be silently wrong too, which is why this runs offline and by hand.
 *
 * The rejection cases are built by putting a bad value through the *generated*
 * Zod validator and assembling exactly the object the generated Pulse
 * assembles, so the fixtures cannot drift from the transpiler output.
 *
 *   cd eval/_run/app && npx tsx epi-eval/selftest.mts
 */

import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { classify, extractRawLabel, labelInEnum, type Outcome } from "./boundary.mts";

let failures = 0;

function check(name: string, actual: unknown, expected: unknown): void {
  const ok = JSON.stringify(actual) === JSON.stringify(expected);
  if (!ok) failures++;
  console.log(
    `${ok ? "  ok  " : "  FAIL"} ${name}` +
      (ok ? "" : `\n         expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`)
  );
}

function branch(name: string, result: unknown, outcome: Outcome, label: string | null): void {
  const got = classify(result);
  check(`${name}: outcome`, got, outcome);
  check(`${name}: raw label`, extractRawLabel(got, result), label);
}

// ---------------------------------------------------------------------------
// Branch 1: validated label, persisted
// ---------------------------------------------------------------------------
branch("persisted", "Correto", "persistido", "Correto");

// ---------------------------------------------------------------------------
// Branch 2: confidence below threshold
// ---------------------------------------------------------------------------
branch(
  "checkpoint",
  {
    _epi_checkpoint: true,
    _epi_strategy: "ReviewRequired",
    confidence: 0.8,
    threshold: 0.85,
    partialResult: { avaliacao: "Parcial" },
  },
  "checkpoint",
  "Parcial"
);

branch(
  "checkpoint with no label in partial",
  {
    _epi_checkpoint: true,
    confidence: 0.5,
    threshold: 0.85,
    partialResult: { comentario: "não sei avaliar" },
  },
  "checkpoint",
  null
);

// ---------------------------------------------------------------------------
// Branch 3a: schema rejection, using the real generated validator
// ---------------------------------------------------------------------------
const validators: any = await import(
  pathToFileURL(resolve("validators/submissao.ts")).href
);
const schema = validators.SubmissaoAvaliacaoSchema;
if (!schema) throw new Error("validators/submissao.ts did not export SubmissaoAvaliacaoSchema");

for (const bad of ["Correct", "CORRETÍSSIMO", "Parcialmente correto", 42]) {
  const parsed = schema.safeParse(bad);
  if (parsed.success) {
    console.log(`  FAIL validator accepted an out-of-enum value: ${JSON.stringify(bad)}`);
    failures++;
    continue;
  }
  // Exactly the object the generated Pulse returns on the Zod failure path.
  const pulseReturn = {
    status: "pending_review",
    queue: "Professores",
    reason: String(parsed.error),
    timestamp: new Date().toISOString(),
  };
  const outcome = classify(pulseReturn);
  check(`schema rejection ${JSON.stringify(bad)}: outcome`, outcome, "fallback_validacao");
  const recovered = extractRawLabel(outcome, pulseReturn);
  // A rejected string must come back verbatim, or the counterfactual count
  // loses the item. A rejected non-string yields null on purpose: Zod reports
  // the offending type, not the offending value, so there is no label to
  // recover. The item still counts as an unguarded write in report.py.
  check(
    `schema rejection ${JSON.stringify(bad)}: raw label`,
    recovered,
    typeof bad === "string" ? bad : null
  );
  check(
    `schema rejection ${JSON.stringify(bad)}: not in enum`,
    labelInEnum(recovered),
    false
  );
}

// ---------------------------------------------------------------------------
// Branch 3b: unparseable model output
// ---------------------------------------------------------------------------
let parseError: unknown;
try {
  JSON.parse("Claro! Aqui está a avaliação:\n```json\n{\"avaliacao\":\"Correto\"}\n```");
} catch (e) {
  parseError = e;
}
branch(
  "unparseable output",
  {
    status: "pending_review",
    queue: "Professores",
    reason: parseError instanceof Error ? parseError.message : "Unknown error",
    timestamp: new Date().toISOString(),
  },
  "fallback_parse",
  null
);

// ---------------------------------------------------------------------------
// Branch 4: contract misread
// ---------------------------------------------------------------------------
branch("unrecognised shape", { algo: "inesperado" }, "erro_harness", null);

// ---------------------------------------------------------------------------
check("enum membership", [labelInEnum("Correto"), labelInEnum("Correct"), labelInEnum(null)],
  [true, false, false]);

console.log(
  failures === 0
    ? "\nself-test passed: the harness reads all four boundary branches correctly."
    : `\nself-test FAILED: ${failures} check(s). Do not trust report.py until this is green.`
);
process.exit(failures === 0 ? 0 : 1);
