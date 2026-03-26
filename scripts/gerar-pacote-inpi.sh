#!/usr/bin/env bash
# gerar-pacote-inpi.sh
# Gera o pacote de registro para o INPI (Programa de Computador)
#
# O INPI exige TRECHO do código-fonte, não o repositório completo.
# Convenção: primeiros 50 + últimos 25 linhas de cada arquivo principal.
# Referência: Instrução Normativa INPI 77/2017 e orientações do e-Nit.

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/inpi-package"
TRECHO="$DIST/trecho-codigo"
DOCS="$DIST/documentos"

echo "==> Preparando pacote INPI em $DIST"
rm -rf "$DIST"
mkdir -p "$TRECHO" "$DOCS"

# ── Documentos descritivos ────────────────────────────────────────────────────
cp "$ROOT/SPEC-PT.md"               "$DOCS/memorial-descritivo.md"
cp "$ROOT/DECLARACAO-AUTORIA-INPI.md" "$DOCS/declaracao-autoria.md"

# ── Trecho de código-fonte ───────────────────────────────────────────────────
# Para cada arquivo principal: primeiras 50 + últimas 25 linhas
# conforme orientação INPI para arquivos de código

extract_trecho() {
  local src="$1"
  local dest="$2"
  mkdir -p "$(dirname "$dest")"
  local total
  total=$(wc -l < "$src")
  if [ "$total" -le 75 ]; then
    # arquivo pequeno — copia inteiro
    cp "$src" "$dest"
  else
    {
      echo "# === TRECHO: primeiras 50 linhas ==="
      head -50 "$src"
      echo ""
      echo "# === [...] ($((total - 75)) linhas omitidas ==="
      echo ""
      echo "# === TRECHO: últimas 25 linhas ==="
      tail -25 "$src"
    } > "$dest"
  fi
}

# Arquivos principais do núcleo
FILES=(
  "grammar/epi.lark"
  "epi/__init__.py"
  "epi/cli.py"
  "epi/parser/ast_nodes.py"
  "epi/parser/builder.py"
  "epi/generators/deterministic/prisma.py"
  "epi/generators/deterministic/validators.py"
  "epi/generators/deterministic/middleware.py"
  "epi/generators/deterministic/routes.py"
  "epi/generators/epistemic/ai_scan.py"
  "epi/generators/epistemic/lens_mood.py"
  "epi/generators/epistemic/traces.py"
  "examples/contrato.epi"
  "examples/edtech-pedagogico.epi"
  "prompts/legal_scan.md"
  "prompts/compreender-enunciado.md"
  "prompts/avaliar-pedagogicamente.md"
)

for f in "${FILES[@]}"; do
  if [ -f "$ROOT/$f" ]; then
    extract_trecho "$ROOT/$f" "$TRECHO/$f"
    echo "  ok  $f"
  else
    echo "  --  $f (não encontrado, pulando)"
  fi
done

# ── Metadados do pacote ──────────────────────────────────────────────────────
cat > "$DIST/README-INPI.txt" << 'EOF'
Epi — Epistemic Programming Interface
Versão 0.3 — 2026-03-25
Autor: Randerson Rebouças

Conteúdo deste pacote:
  documentos/
    memorial-descritivo.md     → Descrição técnica completa (SPEC-PT.md)
    declaracao-autoria.md      → Declaração de autoria e dados do requerente

  trecho-codigo/               → Trecho representativo do código-fonte
    grammar/epi.lark           → Gramática EBNF formal da linguagem
    epi/parser/ast_nodes.py    → Nós da Árvore Sintática Abstrata (AST)
    epi/parser/builder.py      → Transformer Lark → AST
    epi/generators/            → Geradores determinísticos e epistêmicos
    examples/                  → Exemplos de programas .epi
    prompts/                   → Arquivos de prompt externos (artefatos auditáveis)

Instruções:
  1. Preencher DECLARACAO-AUTORIA-INPI.md com dados pessoais (CPF, endereço)
  2. Acessar e-Nit: https://www.gov.br/inpi/pt-br/servicos/programas-de-computador
  3. Fazer upload dos PDFs deste pacote conforme formulário
  4. Pagar GRU (verificar valor vigente para pessoa física)
  5. Aguardar certificado de registro (prazo ~30 dias)

Referências legais:
  Lei 9.609/1998 — Proteção de Programa de Computador
  Lei 9.610/1998 — Direitos Autorais
  IN INPI 77/2017 — Registro de Programa de Computador
EOF

# ── ZIP final ────────────────────────────────────────────────────────────────
cd "$ROOT"
ZIP_NAME="epi-v0.3-inpi-$(date +%Y%m%d).zip"
zip -r "$ZIP_NAME" "inpi-package/" -x "*.DS_Store"
echo ""
echo "==> Pacote gerado: $ROOT/$ZIP_NAME"
echo "    Tamanho: $(du -sh "$ZIP_NAME" | cut -f1)"
echo ""
echo "Próximos passos:"
echo "  1. Preencher CPF e dados em: inpi-package/documentos/declaracao-autoria.md"
echo "  2. Converter os .md para PDF (pandoc, Word, ou Google Docs)"
echo "  3. Acessar: https://www.gov.br/inpi/pt-br/servicos/programas-de-computador"
echo "  4. Fazer upload e pagar GRU"
