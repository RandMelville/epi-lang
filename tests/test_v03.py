"""
Tests for Epi v0.3 features:
- Trace + Checkpoint parsing
- Distribution prior parsing
- confidence_threshold extraction
- Expose: IDENT list parsing
- bayesianUpdate generation
- Trace file generation (store, execution, routes)
"""

from pathlib import Path

import pytest

from epi.parser.builder import parse_epi
from epi.parser.ast_nodes import CheckpointConfig, TraceStep
from epi.generators.deterministic.validators import generate_validators, generate_zod_schema
from epi.generators.epistemic.traces import generate_all_traces, generate_trace_store


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def pedagogico_program():
    source = (EXAMPLES_DIR / "edtech-pedagogico.epi").read_text()
    return parse_epi(source)


# ============================================================
# Trace parsing
# ============================================================

class TestTraceParsing:
    def test_pulse_has_traces(self, pedagogico_program):
        pulse = pedagogico_program.get_pulse("AvaliarRespostaAluno")
        assert pulse is not None
        assert pulse.has_traces is True

    def test_trace_count(self, pedagogico_program):
        pulse = pedagogico_program.get_pulse("AvaliarRespostaAluno")
        assert len(pulse.traces) == 2

    def test_trace_names(self, pedagogico_program):
        pulse = pedagogico_program.get_pulse("AvaliarRespostaAluno")
        names = [t.name for t in pulse.traces]
        assert names == ["CompreenderEnunciado", "AvaliarResposta"]

    def test_trace_is_tracestep_instance(self, pedagogico_program):
        pulse = pedagogico_program.get_pulse("AvaliarRespostaAluno")
        for t in pulse.traces:
            assert isinstance(t, TraceStep)

    def test_trace_has_ai_call(self, pedagogico_program):
        pulse = pedagogico_program.get_pulse("AvaliarRespostaAluno")
        for t in pulse.traces:
            assert t.ai_call is not None
            assert t.ai_call.function in ("reason", "classify", "scan", "generate")

    def test_trace_process_steps_empty_when_traces_present(self, pedagogico_program):
        pulse = pedagogico_program.get_pulse("AvaliarRespostaAluno")
        assert pulse.process_steps == []


# ============================================================
# Checkpoint parsing
# ============================================================

class TestCheckpointParsing:
    def test_unconditional_checkpoint_on_trace_1(self, pedagogico_program):
        pulse = pedagogico_program.get_pulse("AvaliarRespostaAluno")
        trace_1 = pulse.traces[0]
        assert trace_1.checkpoint is not None
        assert isinstance(trace_1.checkpoint, CheckpointConfig)
        assert trace_1.checkpoint.strategy == "ReviewRequired"

    def test_conditional_checkpoint_on_trace_2(self, pedagogico_program):
        pulse = pedagogico_program.get_pulse("AvaliarRespostaAluno")
        trace_2 = pulse.traces[1]
        assert trace_2.checkpoint is None  # no unconditional checkpoint
        assert trace_2.ai_call.on_low_confidence is not None
        assert trace_2.ai_call.on_low_confidence.strategy == "ReviewRequired"

    def test_no_checkpoint_on_trace_1_ai_call(self, pedagogico_program):
        pulse = pedagogico_program.get_pulse("AvaliarRespostaAluno")
        trace_1 = pulse.traces[0]
        assert trace_1.ai_call.on_low_confidence is None


# ============================================================
# Expose: IDENT list parsing
# ============================================================

class TestExposeParsing:
    def test_trace_1_has_expose_fields(self, pedagogico_program):
        pulse = pedagogico_program.get_pulse("AvaliarRespostaAluno")
        trace_1 = pulse.traces[0]
        assert len(trace_1.expose) == 3
        assert "interpretacao" in trace_1.expose
        assert "conceitos_chave" in trace_1.expose
        assert "criterios_avaliacao" in trace_1.expose

    def test_trace_2_has_no_expose(self, pedagogico_program):
        pulse = pedagogico_program.get_pulse("AvaliarRespostaAluno")
        trace_2 = pulse.traces[1]
        assert trace_2.expose == []

    def test_expose_fields_are_plain_strings(self, pedagogico_program):
        pulse = pedagogico_program.get_pulse("AvaliarRespostaAluno")
        for field in pulse.traces[0].expose:
            assert "." not in field, "Expose fields must be plain identifiers, not dotted names"


# ============================================================
# Distribution prior parsing (Dante Barone)
# ============================================================

class TestDistributionPrior:
    def test_avaliacao_field_has_prior(self, pedagogico_program):
        submissao = pedagogico_program.get_entity("Submissao")
        avaliacao = next(f for f in submissao.epistemic_fields if f.name == "avaliacao")
        assert avaliacao.type.prior != {}

    def test_prior_keys_match_enum_values(self, pedagogico_program):
        submissao = pedagogico_program.get_entity("Submissao")
        avaliacao = next(f for f in submissao.epistemic_fields if f.name == "avaliacao")
        prior = avaliacao.type.prior
        assert set(prior.keys()) == {"Correto", "Parcial", "Incorreto"}

    def test_prior_values_are_floats(self, pedagogico_program):
        submissao = pedagogico_program.get_entity("Submissao")
        avaliacao = next(f for f in submissao.epistemic_fields if f.name == "avaliacao")
        for v in avaliacao.type.prior.values():
            assert isinstance(v, float)

    def test_prior_sums_to_one(self, pedagogico_program):
        submissao = pedagogico_program.get_entity("Submissao")
        avaliacao = next(f for f in submissao.epistemic_fields if f.name == "avaliacao")
        total = sum(avaliacao.type.prior.values())
        assert abs(total - 1.0) < 0.01

    def test_confidence_threshold_parsed(self, pedagogico_program):
        submissao = pedagogico_program.get_entity("Submissao")
        avaliacao = next(f for f in submissao.epistemic_fields if f.name == "avaliacao")
        assert avaliacao.type.confidence_threshold == 0.85

    def test_other_fields_have_no_prior(self, pedagogico_program):
        submissao = pedagogico_program.get_entity("Submissao")
        for f in submissao.epistemic_fields:
            if f.name != "avaliacao":
                assert f.type.prior == {}
                assert f.type.confidence_threshold is None


# ============================================================
# Bayesian update generation (Dante Barone)
# ============================================================

class TestBayesianGeneration:
    def test_generates_bayesian_helper(self, pedagogico_program):
        submissao = pedagogico_program.get_entity("Submissao")
        schema = generate_zod_schema(submissao)
        assert schema is not None
        assert "bayesianUpdateSubmissaoAvaliacao" in schema

    def test_bayesian_helper_has_prior(self, pedagogico_program):
        submissao = pedagogico_program.get_entity("Submissao")
        schema = generate_zod_schema(submissao)
        assert '"Correto": 0.4' in schema
        assert '"Parcial": 0.45' in schema
        assert '"Incorreto": 0.15' in schema

    def test_bayesian_helper_normalizes(self, pedagogico_program):
        submissao = pedagogico_program.get_entity("Submissao")
        schema = generate_zod_schema(submissao)
        assert "Normalize" in schema or "normalize" in schema.lower()

    def test_confidence_schema_generated(self, pedagogico_program):
        submissao = pedagogico_program.get_entity("Submissao")
        schema = generate_zod_schema(submissao)
        assert "SubmissaoAvaliacaoSchemaConfidence" in schema
        assert "requiresReview" in schema
        assert "0.85" in schema

    def test_no_bayesian_helper_without_prior(self, pedagogico_program):
        aluno = pedagogico_program.get_entity("Aluno")
        schema = generate_zod_schema(aluno)
        if schema:
            assert "bayesianUpdate" not in schema


# ============================================================
# Trace file generation
# ============================================================

class TestTraceGeneration:
    def test_generates_trace_store(self, pedagogico_program):
        files = generate_all_traces(pedagogico_program)
        assert "lib/trace-store.ts" in files

    def test_trace_store_has_required_exports(self, pedagogico_program):
        files = generate_all_traces(pedagogico_program)
        store = files["lib/trace-store.ts"]
        assert "saveTrace" in store
        assert "getTrace" in store
        assert "updateTrace" in store
        assert "TraceState" in store

    def test_trace_store_has_original_input(self, pedagogico_program):
        files = generate_all_traces(pedagogico_program)
        store = files["lib/trace-store.ts"]
        assert "originalInput" in store

    def test_generates_trace_execution_files(self, pedagogico_program):
        files = generate_all_traces(pedagogico_program)
        assert "traces/avaliar-resposta-aluno/compreender-enunciado.ts" in files
        assert "traces/avaliar-resposta-aluno/avaliar-resposta.ts" in files

    def test_trace_execution_extracts_confidence(self, pedagogico_program):
        files = generate_all_traces(pedagogico_program)
        content = files["traces/avaliar-resposta-aluno/compreender-enunciado.ts"]
        assert "_confidence" in content
        assert "confidence" in content

    def test_trace_execution_has_expose_keys(self, pedagogico_program):
        files = generate_all_traces(pedagogico_program)
        content = files["traces/avaliar-resposta-aluno/compreender-enunciado.ts"]
        assert "interpretacao" in content
        assert "conceitos_chave" in content

    def test_unconditional_checkpoint_pauses_always(self, pedagogico_program):
        files = generate_all_traces(pedagogico_program)
        content = files["traces/avaliar-resposta-aluno/compreender-enunciado.ts"]
        assert "shouldPause = true" in content

    def test_conditional_checkpoint_uses_threshold(self, pedagogico_program):
        files = generate_all_traces(pedagogico_program)
        content = files["traces/avaliar-resposta-aluno/avaliar-resposta.ts"]
        assert "shouldPause = confidence <" in content

    def test_generates_inspect_route(self, pedagogico_program):
        files = generate_all_traces(pedagogico_program)
        assert "app/api/traces/avaliar-resposta-aluno/[traceId]/inspect/route.ts" in files

    def test_generates_resume_route(self, pedagogico_program):
        files = generate_all_traces(pedagogico_program)
        assert "app/api/traces/avaliar-resposta-aluno/[traceId]/resume/route.ts" in files

    def test_resume_route_chains_next_trace(self, pedagogico_program):
        files = generate_all_traces(pedagogico_program)
        resume = files["app/api/traces/avaliar-resposta-aluno/[traceId]/resume/route.ts"]
        assert "executeAvaliarResposta" in resume
        assert "nextTrace" in resume

    def test_resume_route_handles_last_trace(self, pedagogico_program):
        files = generate_all_traces(pedagogico_program)
        resume = files["app/api/traces/avaliar-resposta-aluno/[traceId]/resume/route.ts"]
        assert "pipelineStatus" in resume

    def test_no_trace_files_for_non_trace_pulse(self):
        # A program with only classic Process: pulses generates no trace files
        src = '''
@Language: Epi v0.3
@Goal: "test"
Entity Foo { id: UUID(auto), nome: Text }
Guard G { Condition: Auth.Role == "Admin" }
Pulse P {
    Input: Foo
    Process:
        Execute: AI.scan(
            source: Input.nome,
            prompt: file("@prompts/test.md"),
            temperature: 0.5,
            on_fail: Fallback.ReturnEmpty
        )
}
Pipeline Pipe { Flow: P -> P }
'''
        program = parse_epi(src)
        files = generate_all_traces(program)
        assert files == {}


# ============================================================
# AI.reason() parsing
# ============================================================

class TestAIReason:
    def test_reason_parsed_as_function(self, pedagogico_program):
        pulse = pedagogico_program.get_pulse("AvaliarRespostaAluno")
        trace_1 = pulse.traces[0]
        assert trace_1.ai_call.function == "reason"

    def test_reason_has_temperature(self, pedagogico_program):
        pulse = pedagogico_program.get_pulse("AvaliarRespostaAluno")
        trace_1 = pulse.traces[0]
        assert "temperature" in trace_1.ai_call.args


# ============================================================
# Guard fix: returns NextResponse | null
# ============================================================

class TestGuardFix:
    def test_guard_returns_null_on_allow(self):
        from epi.generators.deterministic.middleware import generate_middleware
        src = '''
@Language: Epi v0.3
@Goal: "test"
Entity X { id: UUID(auto) }
Guard OnlyAdmin { Condition: Auth.Role == "Admin" }
'''
        program = parse_epi(src)
        files = generate_middleware(program, "nextjs")
        content = files["middleware/only-admin.ts"]
        assert "return null;" in content

    def test_guard_return_type_is_nexresponse_or_null(self):
        from epi.generators.deterministic.middleware import generate_middleware
        src = '''
@Language: Epi v0.3
@Goal: "test"
Entity X { id: UUID(auto) }
Guard OnlyTeacher { Condition: Auth.Role == "Teacher" }
'''
        program = parse_epi(src)
        files = generate_middleware(program, "nextjs")
        content = files["middleware/only-teacher.ts"]
        assert "NextResponse | null" in content
