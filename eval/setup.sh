#!/usr/bin/env bash
#
# Epi containment harness: one-shot setup.
#
# Transpiles two .epi programs that differ in a single token, installs each
# generated app's dependencies, and drops the harness inside them. After this
# runs, the driver imports the *generated* Pulse directly, unmodified.
#
#   v1  examples/avaliacao-simples.epi        source: Input.resposta_aluno
#       (the program reproduced in the paper)
#   v2  eval/variants/fonte-completa.epi      source: Input
#       (same epistemic contract, question visible to the model)
#
#   ./eval/setup.sh
#
# Then follow the printed instructions to run each condition.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$REPO_ROOT/eval/_run"

# The epi CLI needs Python >= 3.10 (pydantic models use PEP 604 unions).
PY="${PY:-$REPO_ROOT/.venv/bin/python}"
if [ ! -x "$PY" ]; then
  echo "error: $PY not found. Set PY=/path/to/python3.12 or create .venv." >&2
  exit 1
fi

build_variant() {
  local name="$1"
  local epi_file="$2"
  local app_dir="$RUN_DIR/$name"

  echo "==> [$name] transpiling $(basename "$epi_file")"
  rm -rf "$app_dir"
  mkdir -p "$app_dir"
  (cd "$REPO_ROOT" && "$PY" -m epi.cli transpile "$epi_file" --outdir "$app_dir" >/dev/null)

  if [ ! -f "$app_dir/pulses/avaliar-resposta.ts" ]; then
    echo "error: [$name] transpiler did not emit pulses/avaliar-resposta.ts" >&2
    exit 1
  fi

  echo "==> [$name] installing generated app dependencies"
  cd "$app_dir"
  # The postinstall hook runs prisma generate, which the harness never needs.
  cp .env.example .env
  npm install --silent --ignore-scripts
  npm install --silent --no-save tsx

  mkdir -p "$app_dir/epi-eval"
  cp "$REPO_ROOT/eval/driver.mts" \
     "$REPO_ROOT/eval/boundary.mts" \
     "$REPO_ROOT/eval/selftest.mts" \
     "$REPO_ROOT/eval/dataset.jsonl" \
     "$app_dir/epi-eval/"
  cd "$REPO_ROOT"
}

build_variant v1 "$REPO_ROOT/examples/avaliacao-simples.epi"
build_variant v2 "$REPO_ROOT/eval/variants/fonte-completa.epi"

echo "==> Verifying the two variants differ only in the AI call source"
if diff <(grep -c . "$RUN_DIR/v1/pulses/avaliar-resposta.ts") \
        <(grep -c . "$RUN_DIR/v2/pulses/avaliar-resposta.ts") >/dev/null; then
  echo "    generated Pulses have the same shape (expected)"
fi
diff "$RUN_DIR/v1/pulses/avaliar-resposta.ts" "$RUN_DIR/v2/pulses/avaliar-resposta.ts" \
  | grep -E '^[<>]' || true

echo "==> Running the harness self-test (no model calls)"
(cd "$RUN_DIR/v1" && npx tsx epi-eval/selftest.mts | tail -1)

cat <<'EOF'

Setup complete.

Local model (needs `ollama serve` and `ollama pull qwen2.5:3b-instruct`):

  cd eval/_run/v1 && EPI_AI_PROVIDER=ollama EPI_AI_MODEL=qwen2.5:3b-instruct \
    EPI_AI_BASE_URL=http://localhost:11434/v1 \
    npx tsx epi-eval/driver.mts --repeats 3 --variant v1-resposta \
    --out ../../results-ollama-v1.jsonl

  cd eval/_run/v2 && EPI_AI_PROVIDER=ollama EPI_AI_MODEL=qwen2.5:3b-instruct \
    EPI_AI_BASE_URL=http://localhost:11434/v1 \
    npx tsx epi-eval/driver.mts --repeats 3 --variant v2-fonte-completa \
    --out ../../results-ollama-v2.jsonl

Cloud model (needs ANTHROPIC_API_KEY; 120 short calls per variant):

  cd eval/_run/v1 && EPI_AI_PROVIDER=anthropic EPI_AI_MODEL=claude-sonnet-4-20250514 \
    npx tsx epi-eval/driver.mts --repeats 3 --variant v1-resposta \
    --out ../../results-anthropic-v1.jsonl

  cd eval/_run/v2 && EPI_AI_PROVIDER=anthropic EPI_AI_MODEL=claude-sonnet-4-20250514 \
    npx tsx epi-eval/driver.mts --repeats 3 --variant v2-fonte-completa \
    --out ../../results-anthropic-v2.jsonl

Report:

  python3 eval/report.py eval/results-*.jsonl --latex

EOF
