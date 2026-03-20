"""
Tests for the Epi parser — grammar, transformer, and AST construction.
"""

from pathlib import Path

import pytest

from epi.parser.ast_nodes import TypeDomain
from epi.parser.builder import parse_epi


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


# ============================================================
# Fixture: parse the canonical example once
# ============================================================

@pytest.fixture(scope="module")
def contrato_program():
    source = (EXAMPLES_DIR / "contrato.epi").read_text()
    return parse_epi(source)


@pytest.fixture(scope="module")
def edtech_program():
    path = EXAMPLES_DIR / "edtech.epi"
    if path.exists():
        return parse_epi(path.read_text())
    return None


# ============================================================
# Metadata
# ============================================================

class TestMetadata:
    def test_language_version_preserves_dot(self, contrato_program):
        meta = contrato_program.metadata[0]
        assert meta.key == "Language"
        assert meta.value == "Epi v0.2"

    def test_goal_parsed(self, contrato_program):
        goals = [m for m in contrato_program.metadata if m.key == "Goal"]
        assert len(goals) == 1


# ============================================================
# Entity + Epistemic Type System
# ============================================================

class TestEntity:
    def test_entity_count(self, contrato_program):
        assert len(contrato_program.entities) == 2

    def test_entity_names(self, contrato_program):
        names = [e.name for e in contrato_program.entities]
        assert "Contrato" in names
        assert "Advogado" in names

    def test_rigid_fields(self, contrato_program):
        contrato = contrato_program.get_entity("Contrato")
        rigid = contrato.rigid_fields
        assert len(rigid) == 5
        rigid_names = {f.name for f in rigid}
        assert rigid_names == {"id", "titulo", "documento", "valor", "criado_em"}

    def test_epistemic_fields(self, contrato_program):
        contrato = contrato_program.get_entity("Contrato")
        epistemic = contrato.epistemic_fields
        assert len(epistemic) == 1
        assert epistemic[0].name == "risco"

    def test_epistemic_domain_classification(self, contrato_program):
        contrato = contrato_program.get_entity("Contrato")
        for f in contrato.fields:
            if f.name == "risco":
                assert f.type.domain == TypeDomain.EPISTEMIC
            else:
                assert f.type.domain == TypeDomain.RIGID

    def test_uuid_auto_modifier(self, contrato_program):
        contrato = contrato_program.get_entity("Contrato")
        id_field = next(f for f in contrato.fields if f.name == "id")
        assert id_field.type.base == "UUID"
        assert id_field.type.modifiers.get("auto") is True

    def test_datetime_auto_modifier(self, contrato_program):
        contrato = contrato_program.get_entity("Contrato")
        dt_field = next(f for f in contrato.fields if f.name == "criado_em")
        assert dt_field.type.base == "DateTime"
        assert dt_field.type.modifiers.get("auto") is True

    def test_ai_enum_values(self, contrato_program):
        contrato = contrato_program.get_entity("Contrato")
        risco = next(f for f in contrato.fields if f.name == "risco")
        assert risco.type.kind == "Enum"
        assert risco.type.enum_values == ["Alto", "Medio", "Baixo"]
        assert risco.type.args.get("strict") is True

    def test_ai_text_max_tokens(self, contrato_program):
        advogado = contrato_program.get_entity("Advogado")
        esp = next(f for f in advogado.fields if f.name == "especialidade")
        assert esp.type.kind == "Text"
        assert esp.type.args.get("max_tokens") == 50


# ============================================================
# Guard
# ============================================================

class TestGuard:
    def test_guard_count(self, contrato_program):
        assert len(contrato_program.guards) == 2

    def test_guard_condition(self, contrato_program):
        guard = contrato_program.get_guard("SomenteAdvogados")
        assert guard is not None
        assert len(guard.conditions) == 1
        cond = guard.conditions[0]
        assert cond.left == "Auth.Role"
        assert cond.operator == "=="
        assert cond.right == "Lawyer"


# ============================================================
# Pulse
# ============================================================

class TestPulse:
    def test_pulse_count(self, contrato_program):
        assert len(contrato_program.pulses) == 3

    def test_pulse_input_entity(self, contrato_program):
        pulse = contrato_program.get_pulse("ExtrairRisco")
        assert pulse.input_entity == "Contrato"

    def test_pulse_guard_ref(self, contrato_program):
        pulse = contrato_program.get_pulse("ExtrairRisco")
        assert pulse.guard_ref == "Guard.SomenteAdvogados"

    def test_pulse_without_guard(self, contrato_program):
        pulse = contrato_program.get_pulse("Notificar")
        assert pulse.guard_ref is None

    def test_ai_call_function(self, contrato_program):
        pulse = contrato_program.get_pulse("ExtrairRisco")
        assert len(pulse.process_steps) == 1
        assert pulse.process_steps[0].function == "scan"

    def test_ai_call_temperature(self, contrato_program):
        pulse = contrato_program.get_pulse("ExtrairRisco")
        assert pulse.process_steps[0].args.get("temperature") == 0.1

    def test_ai_call_prompt_file(self, contrato_program):
        pulse = contrato_program.get_pulse("ExtrairRisco")
        assert pulse.process_steps[0].prompt_file == "@prompts/legal_scan.md"

    def test_fallback_strategy(self, contrato_program):
        pulse = contrato_program.get_pulse("ExtrairRisco")
        fb = pulse.process_steps[0].fallback
        assert fb is not None
        assert fb.strategy == "ManualReview"
        assert fb.params.get("Queue") == "Advogados"

    def test_fallback_return_empty(self, contrato_program):
        pulse = contrato_program.get_pulse("GerarResumo")
        fb = pulse.process_steps[0].fallback
        assert fb.strategy == "ReturnEmpty"

    def test_pulse_output_ref(self, contrato_program):
        pulse = contrato_program.get_pulse("ExtrairRisco")
        assert pulse.output_ref == "Contrato.risco"


# ============================================================
# Pipeline
# ============================================================

class TestPipeline:
    def test_pipeline_count(self, contrato_program):
        assert len(contrato_program.pipelines) == 1

    def test_pipeline_flow(self, contrato_program):
        pipe = contrato_program.pipelines[0]
        assert pipe.flow == ["ExtrairRisco", "GerarResumo", "Notificar"]

    def test_pipeline_error_strategy(self, contrato_program):
        pipe = contrato_program.pipelines[0]
        assert pipe.on_error is not None
        assert pipe.on_error.strategy == "Retry"
        assert pipe.on_error.params.get("max") == 3
        assert pipe.on_error.params.get("backoff") == "exponential"


# ============================================================
# Lens
# ============================================================

class TestLens:
    def test_lens_count(self, contrato_program):
        assert len(contrato_program.lenses) == 1

    def test_lens_mood(self, contrato_program):
        lens = contrato_program.lenses[0]
        assert lens.mood == "Clean, Legal-Tech, Professional"

    def test_table_widget_entity(self, contrato_program):
        table = contrato_program.lenses[0].display[0]
        assert table.widget_type == "Table"
        assert table.args.get("entity") == "Contrato"
        assert table.args.get("columns") == ["titulo", "valor", "risco", "criado_em"]

    def test_form_widget_entity(self, contrato_program):
        form = contrato_program.lenses[0].display[1]
        assert form.widget_type == "Form"
        assert form.args.get("entity") == "Contrato"

    def test_form_chain_button(self, contrato_program):
        form = contrato_program.lenses[0].display[1]
        assert form.chain is not None
        assert form.chain.widget_type == "Button"
        assert form.chain.args.get("label") == "Analisar Risco"
        assert form.chain.trigger.pulse_name == "ExtrairRisco"

    def test_standalone_button(self, contrato_program):
        btn = contrato_program.lenses[0].display[2]
        assert btn.widget_type == "Button"
        assert btn.args.get("label") == "Gerar Resumo"
        assert btn.trigger.pulse_name == "GerarResumo"

    def test_inject_html(self, contrato_program):
        lens = contrato_program.lenses[0]
        assert lens.inject is not None
        assert "footer" in lens.inject


# ============================================================
# Edge cases
# ============================================================

class TestEdgeCases:
    def test_empty_entity(self):
        source = 'Entity Empty { id: UUID(auto) }'
        program = parse_epi(source)
        assert len(program.entities) == 1
        assert program.entities[0].name == "Empty"

    def test_minimal_guard(self):
        source = 'Guard Admin { Condition: Auth.Role == "Admin" }'
        program = parse_epi(source)
        assert len(program.guards) == 1

    def test_minimal_pipeline(self):
        source = """
        Pulse A { Input: X Process: Execute: AI.scan(source: Input.data, prompt: file("@p/a.md"), temperature: 0.5, on_fail: Fallback.ReturnEmpty) }
        Pipeline P { Flow: A -> A }
        """
        program = parse_epi(source)
        assert program.pipelines[0].flow == ["A", "A"]

    def test_program_lookup_miss(self, contrato_program):
        assert contrato_program.get_entity("NonExistent") is None
        assert contrato_program.get_guard("NonExistent") is None
        assert contrato_program.get_pulse("NonExistent") is None
