"""
Epi AST Nodes — Pydantic models representing the typed Abstract Syntax Tree.

The AST separates into two domains:
- Deterministic nodes: Entity fields with rigid types, Guards, Pipelines
- Epistemic nodes: AI.* types, AI.* calls, Fallbacks, Lens Mood

This separation IS the Epistemic Type System in action.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# ============================================================
# Shared
# ============================================================

class Metadata(BaseModel):
    key: str
    value: str


# ============================================================
# Type System — The Epistemic Core
# ============================================================

class TypeDomain(str, Enum):
    """The epistemic classification of a type."""
    RIGID = "rigid"          # Deterministic — maps to DB column, no AI involved
    EPISTEMIC = "epistemic"  # AI-inferred — validated at runtime via Zod/Pydantic


class RigidType(BaseModel):
    domain: Literal[TypeDomain.RIGID] = TypeDomain.RIGID
    base: str  # UUID, Text, Int, Float, Decimal, Bool, DateTime, JSON
    modifiers: dict[str, str | bool | None] = Field(default_factory=dict)


class EpistemicType(BaseModel):
    domain: Literal[TypeDomain.EPISTEMIC] = TypeDomain.EPISTEMIC
    kind: str  # Enum, Text, Classification, Embedding, Score
    args: dict[str, str | bool | int | float | list[str] | None] = Field(default_factory=dict)
    enum_values: list[str] = Field(default_factory=list)


FieldType = RigidType | EpistemicType


class EntityField(BaseModel):
    name: str
    type: FieldType


# ============================================================
# Entity
# ============================================================

class Entity(BaseModel):
    name: str
    fields: list[EntityField]

    @property
    def rigid_fields(self) -> list[EntityField]:
        return [f for f in self.fields if f.type.domain == TypeDomain.RIGID]

    @property
    def epistemic_fields(self) -> list[EntityField]:
        return [f for f in self.fields if f.type.domain == TypeDomain.EPISTEMIC]


# ============================================================
# Guard
# ============================================================

class Condition(BaseModel):
    left: str        # e.g. "Auth.Role"
    operator: str    # e.g. "=="
    right: str       # e.g. "Admin"


class Guard(BaseModel):
    name: str
    conditions: list[Condition]
    logic: str = "&&"  # "&&" or "||"


# ============================================================
# Pulse — Logic + Hallucination Control
# ============================================================

class FallbackConfig(BaseModel):
    strategy: str  # ManualReview, ReturnEmpty, ReturnDefault, Retry, Escalate
    params: dict[str, str] = Field(default_factory=dict)


class AICall(BaseModel):
    function: str  # scan, summarize, classify, extract, generate, embed
    args: dict[str, str | float | int | None] = Field(default_factory=dict)
    prompt_file: str | None = None
    fallback: FallbackConfig | None = None


class Pulse(BaseModel):
    name: str
    input_entity: str
    guard_ref: str | None = None
    process_steps: list[AICall]
    output_ref: str | None = None


# ============================================================
# Pipeline — Flow Composition
# ============================================================

class ErrorStrategy(BaseModel):
    strategy: str  # Retry, Halt, Fallback
    params: dict[str, str | int | float] = Field(default_factory=dict)


class Pipeline(BaseModel):
    name: str
    flow: list[str]  # ordered list of Pulse/step names
    on_error: ErrorStrategy | None = None


# ============================================================
# Lens — Semantic UI + Escape Hatch
# ============================================================

class WidgetTrigger(BaseModel):
    pulse_name: str


class Widget(BaseModel):
    widget_type: str  # Table, Form, Card, List, Chart, Button, Input, Modal
    args: dict[str, str | list[str]] = Field(default_factory=dict)
    trigger: WidgetTrigger | None = None
    chain: Widget | None = None


class Lens(BaseModel):
    name: str
    mood: str | None = None
    display: list[Widget] = Field(default_factory=list)
    inject: str | None = None


# ============================================================
# Program — The root AST node
# ============================================================

class EpiProgram(BaseModel):
    """Root node of an Epi AST. Represents a complete .epi file."""
    metadata: list[Metadata] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    guards: list[Guard] = Field(default_factory=list)
    pulses: list[Pulse] = Field(default_factory=list)
    pipelines: list[Pipeline] = Field(default_factory=list)
    lenses: list[Lens] = Field(default_factory=list)

    def get_entity(self, name: str) -> Entity | None:
        return next((e for e in self.entities if e.name == name), None)

    def get_guard(self, name: str) -> Guard | None:
        return next((g for g in self.guards if g.name == name), None)

    def get_pulse(self, name: str) -> Pulse | None:
        return next((p for p in self.pulses if p.name == name), None)
