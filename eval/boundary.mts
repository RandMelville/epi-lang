/**
 * Epi containment harness: reading the generated boundary's verdict.
 *
 * This module interprets what the generated Pulse returned. It deliberately
 * contains no decision logic of its own: the threshold comparison and the Zod
 * validation happen in transpiler output, and everything here is read-only
 * inspection of the value that came back.
 *
 * The four shapes a generated Pulse can return (see
 * epi/generators/epistemic/ai_scan.py):
 *
 *   1. a bare string                -> validated label, persisted
 *   2. { _epi_checkpoint: true }    -> confidence below threshold
 *   3. { status: "pending_review" } -> Fallback.ManualReview, from either
 *                                      the JSON.parse catch or the Zod failure
 *   4. anything else                -> the harness misread the contract
 */

export const ENUM_LABELS = ["Correto", "Parcial", "Incorreto"];

export type Outcome =
  | "persistido"
  | "checkpoint"
  | "fallback_parse"
  | "fallback_validacao"
  | "erro_harness";

export function classify(result: unknown): Outcome {
  if (typeof result === "string") return "persistido";
  if (result && typeof result === "object") {
    const r = result as Record<string, unknown>;
    if (r._epi_checkpoint === true) return "checkpoint";
    if (r.status === "pending_review") {
      const reason = String(r.reason ?? "");
      // The generated code funnels both failure modes into the same shape.
      // A Zod error serialises its issue array; a JSON.parse error is a plain
      // syntax message, so the presence of issue fields separates them.
      const isZod = reason.includes('"code"') || reason.includes("invalid_");
      return isZod ? "fallback_validacao" : "fallback_parse";
    }
  }
  return "erro_harness";
}

/**
 * Recover the label the model actually produced, whatever branch fired.
 *
 * This is what makes the counterfactual computable. To claim that the boundary
 * kept N wrong values out of the database, we need to know what would have
 * been written had the boundary not been there, including for the items the
 * boundary rejected.
 *
 *   persisted        -> the return value IS the validated label
 *   checkpoint       -> partialResult still carries the raw object
 *   validation fail  -> Zod's issue list carries `received`
 *   parse fail       -> nothing to recover; there was no label at all
 */
export function extractRawLabel(outcome: Outcome, result: any): string | null {
  if (outcome === "persistido") return String(result);

  if (outcome === "checkpoint") {
    const partial = result?.partialResult;
    if (typeof partial === "string") return partial;
    if (partial && typeof partial === "object" && "avaliacao" in partial) {
      const v = (partial as Record<string, unknown>).avaliacao;
      return v === null || v === undefined ? null : String(v);
    }
    return null;
  }

  if (outcome === "fallback_validacao") {
    const reason = String(result?.reason ?? "");
    // String(ZodError) serialises the issue array, so parse it rather than
    // pattern-matching the text.
    //
    // The `received` field means two different things depending on the issue
    // code: for invalid_enum_value it is the offending *value*, but for
    // invalid_type it is the offending *type name* ("number", "object"). Only
    // the former is a label. Reading the latter as one would record a model
    // output of "number", which never happened.
    const issues = parseIssues(reason);
    if (issues) {
      for (const issue of issues) {
        const code = String(issue?.code ?? "");
        if (code === "invalid_type") return null;
        if ("received" in (issue ?? {})) {
          const recv = issue.received;
          return typeof recv === "string" ? recv : String(recv);
        }
      }
      return null;
    }

    // Fallback for a reason string that is not parseable JSON: only trust it
    // when no invalid_type issue is mentioned.
    if (reason.includes("invalid_type")) return null;
    const m = reason.match(/"received"\s*:\s*("(?:[^"\\]|\\.)*"|[^,\n}]+)/);
    if (!m) return null;
    try {
      return String(JSON.parse(m[1]));
    } catch {
      return m[1].trim();
    }
  }

  return null;
}

function parseIssues(reason: string): any[] | null {
  const start = reason.indexOf("[");
  const end = reason.lastIndexOf("]");
  if (start === -1 || end <= start) return null;
  try {
    const parsed = JSON.parse(reason.slice(start, end + 1));
    return Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

export function labelInEnum(label: string | null): boolean {
  return label !== null && ENUM_LABELS.includes(label);
}
