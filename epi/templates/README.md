# Epi Starter Project

This directory was bootstrapped by `epi init`. It contains the smallest viable
Epi program — one Entity, one Guard, one Pulse — that classifies contract risk
via an LLM with a confidence-aware human-review checkpoint.

## Quickstart

1. **Inspect / edit the contract**

   Open `contrato.epi`. The file defines:
   - `Entity Contrato` — one rigid field (`documento`) and one epistemic field (`risco`)
   - `Guard SomenteAdvogados` — only `Auth.Role == "Lawyer"` may invoke the pulse
   - `Pulse ClassificarRisco` — calls `AI.scan(...)` with a confidence threshold

   The prompt lives in `prompts/legal_scan_simples.md` and returns JSON with
   `risco` (enum) and `_confidence` (0.0–1.0).

2. **Transpile to a Next.js project**

   ```bash
   epi transpile contrato.epi --target nextjs --outdir ./app
   ```

   This generates a complete Next.js + Prisma + LLM scaffold under `./app/`.

3. **Configure an LLM provider**

   ```bash
   cd app
   npm install
   cp .env.example .env
   ```

   Edit `.env` and pick **one** provider:

   - **Anthropic Claude** (cloud):
     ```
     EPI_AI_PROVIDER=anthropic
     EPI_AI_MODEL=claude-sonnet-4-20250514
     ANTHROPIC_API_KEY=sk-ant-...
     ```
   - **Ollama** (local, no API key, requires `ollama serve`):
     ```
     EPI_AI_PROVIDER=ollama
     EPI_AI_MODEL=qwen2.5:3b-instruct
     EPI_AI_BASE_URL=http://localhost:11434/v1
     ```

4. **Run migrations and start the dev server**

   ```bash
   npx prisma migrate dev --name init
   npm run dev
   ```

## What to try next

- Edit `contrato.epi` to add a second epistemic field (e.g. `categoria`).
- Lower `confidence_threshold` and observe how more results auto-apply.
- Inspect a paused trace at `/api/traces/analisar-contrato/<traceId>/inspect`
  and resume it via the `resume` route.

See the full language reference at <https://github.com/RandMelville/epi-lang>.
