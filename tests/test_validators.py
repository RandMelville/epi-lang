"""
Tests for Zod validator generation — the proof of "if it compiles, it validates".
"""

from pathlib import Path

import pytest

from epi.parser.builder import parse_epi
from epi.generators.deterministic.validators import generate_validators, generate_zod_schema


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.fixture(scope="module")
def contrato_program():
    source = (EXAMPLES_DIR / "contrato.epi").read_text()
    return parse_epi(source)


@pytest.fixture(scope="module")
def edtech_program():
    source = (EXAMPLES_DIR / "edtech.epi").read_text()
    return parse_epi(source)


# ============================================================
# Contrato example
# ============================================================

class TestContratoValidators:
    def test_generates_validator_for_contrato(self, contrato_program):
        files = generate_validators(contrato_program)
        assert "validators/contrato.ts" in files

    def test_generates_validator_for_advogado(self, contrato_program):
        files = generate_validators(contrato_program)
        assert "validators/advogado.ts" in files

    def test_contrato_enum_validator(self, contrato_program):
        files = generate_validators(contrato_program)
        content = files["validators/contrato.ts"]
        assert 'z.enum(["Alto", "Medio", "Baixo"])' in content

    def test_contrato_strict_enum_no_optional(self, contrato_program):
        files = generate_validators(contrato_program)
        content = files["validators/contrato.ts"]
        # strict: true means no .optional()
        assert ".optional()" not in content

    def test_advogado_text_max_tokens(self, contrato_program):
        files = generate_validators(contrato_program)
        content = files["validators/advogado.ts"]
        # max_tokens: 50 → max chars: 200
        assert ".max(200)" in content

    def test_combined_schema(self, contrato_program):
        files = generate_validators(contrato_program)
        content = files["validators/contrato.ts"]
        assert "ContratoEpistemicSchema = z.object" in content
        assert "z.infer<typeof ContratoEpistemicSchema>" in content

    def test_zod_import(self, contrato_program):
        files = generate_validators(contrato_program)
        for content in files.values():
            assert 'import { z } from "zod"' in content


# ============================================================
# EdTech example — more epistemic types
# ============================================================

class TestEdTechValidators:
    def test_generates_3_validator_files(self, edtech_program):
        files = generate_validators(edtech_program)
        assert len(files) == 3
        assert "validators/student.ts" in files
        assert "validators/assignment.ts" in files
        assert "validators/submission.ts" in files

    def test_score_validator_min_max(self, edtech_program):
        files = generate_validators(edtech_program)
        content = files["validators/assignment.ts"]
        assert "z.number().min(0).max(1)" in content

    def test_score_grade_0_100(self, edtech_program):
        files = generate_validators(edtech_program)
        content = files["validators/submission.ts"]
        assert "z.number().min(0).max(100)" in content

    def test_text_feedback_max(self, edtech_program):
        files = generate_validators(edtech_program)
        content = files["validators/submission.ts"]
        # max_tokens: 500 → max chars: 2000
        assert ".max(2000)" in content

    def test_enum_plagiarism(self, edtech_program):
        files = generate_validators(edtech_program)
        content = files["validators/submission.ts"]
        assert '"None"' in content
        assert '"Low"' in content
        assert '"High"' in content

    def test_submission_combined_schema_3_fields(self, edtech_program):
        files = generate_validators(edtech_program)
        content = files["validators/submission.ts"]
        assert "grade: SubmissionGradeSchema" in content
        assert "feedback: SubmissionFeedbackSchema" in content
        assert "plagiarism_risk: SubmissionPlagiarism_riskSchema" in content


# ============================================================
# Edge cases
# ============================================================

class TestValidatorEdgeCases:
    def test_entity_without_epistemic_fields_returns_none(self):
        source = 'Entity Simple { id: UUID(auto), name: Text }'
        program = parse_epi(source)
        schema = generate_zod_schema(program.entities[0])
        assert schema is None

    def test_entity_without_epistemic_fields_not_in_files(self):
        source = 'Entity Simple { id: UUID(auto), name: Text }'
        program = parse_epi(source)
        files = generate_validators(program)
        assert len(files) == 0

    def test_consistent_naming(self, edtech_program):
        """Schema names used in individual exports must match z.object references."""
        files = generate_validators(edtech_program)
        for content in files.values():
            lines = content.split("\n")
            # Find z.object entries
            for line in lines:
                if ": " in line and "Schema," in line:
                    # e.g. "  grade: SubmissionGradeSchema,"
                    ref_name = line.strip().split(": ")[1].rstrip(",")
                    # Must exist as an export
                    assert f"export const {ref_name}" in content, \
                        f"{ref_name} referenced in z.object but not exported"
