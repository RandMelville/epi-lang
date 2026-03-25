"""
Epi Parser — Lark grammar → Typed AST (Pydantic)

This is the deterministic layer of the Epistemic Transpiler.
No LLM involvement here — pure formal parsing.

v0.3 additions:
- distribution_ref / distribution_entries / distribution_entry → prior dict
- checkpoint_ref / checkpoint_params → CheckpointConfig
- pulse_traces / trace / trace_body / trace_expose / trace_checkpoint → TraceStep
- Updated epistemic_type: extracts prior + confidence_threshold from args
- Updated ai_call: extracts on_low_confidence from args
"""

from __future__ import annotations

import json
from pathlib import Path

from lark import Lark, Transformer, v_args

from epi.parser.ast_nodes import (
    AICall,
    CheckpointConfig,
    Condition,
    Entity,
    EntityField,
    EpiProgram,
    EpistemicType,
    ErrorStrategy,
    FallbackConfig,
    Guard,
    Lens,
    Metadata,
    Pipeline,
    Pulse,
    RigidType,
    TraceStep,
    Widget,
    WidgetTrigger,
)

GRAMMAR_PATH = Path(__file__).parent.parent.parent / "grammar" / "epi.lark"


def _get_parser() -> Lark:
    return Lark(
        GRAMMAR_PATH.read_text(),
        parser="earley",
        ambiguity="resolve",
    )


@v_args(inline=True)
class EpiTransformer(Transformer):
    """Transforms Lark parse tree into typed Epi AST nodes."""

    def start(self, *items):
        program = EpiProgram()
        for item in items:
            if isinstance(item, Metadata):
                program.metadata.append(item)
            elif isinstance(item, Entity):
                program.entities.append(item)
            elif isinstance(item, Guard):
                program.guards.append(item)
            elif isinstance(item, Pulse):
                program.pulses.append(item)
            elif isinstance(item, Pipeline):
                program.pipelines.append(item)
            elif isinstance(item, Lens):
                program.lenses.append(item)
        return program

    # --- Metadata ---
    def metadata(self, key, value):
        return Metadata(key=str(key), value=str(value))

    def metadata_value(self, *parts):
        return " ".join(str(p) for p in parts)

    def metadata_text(self, *parts):
        # Reconstruct version strings like "Epi v0.2"
        result = []
        for p in parts:
            s = str(p)
            if result and s != "." and result[-1] != ".":
                result.append(" ")
            result.append(s)
        return "".join(result)

    def VERSION(self, token):
        return str(token)

    def METADATA_KEY(self, token):
        return str(token)

    # --- Declaration passthrough ---
    def declaration(self, item):
        return item

    # --- Entity ---
    def entity(self, name, *fields):
        return Entity(name=str(name), fields=list(fields))

    def field(self, name, type_expr):
        return EntityField(name=str(name), type=type_expr)

    def type_expr(self, t):
        return t

    def rigid_type(self, base, modifier=None):
        modifiers = modifier if isinstance(modifier, dict) else {}
        return RigidType(base=str(base), modifiers=modifiers)

    def BASE_TYPE(self, token):
        return str(token)

    def type_modifier(self, args):
        return args

    def modifier_args(self, *args):
        result = {}
        for arg in args:
            if isinstance(arg, tuple):
                result[arg[0]] = arg[1]
            else:
                result[str(arg)] = True
        return result

    def modifier_arg(self, name, value=None):
        if value is not None:
            return (str(name), str(value))
        return str(name)

    def epistemic_type(self, kind, args_data):
        kind_str = str(kind)
        enum_values = []
        params = {}

        if isinstance(args_data, dict):
            params = dict(args_data.get("params", {}))
            enum_values = args_data.get("enum_values", [])

        # v0.3: extract prior and confidence_threshold from params
        prior: dict[str, float] = {}
        confidence_threshold: float | None = None

        if isinstance(params.get("prior"), dict):
            prior = params.pop("prior")
        if "confidence_threshold" in params:
            ct = params.pop("confidence_threshold")
            try:
                confidence_threshold = float(ct)
            except (TypeError, ValueError):
                confidence_threshold = None

        return EpistemicType(
            kind=kind_str,
            args=params,
            enum_values=enum_values,
            prior=prior,
            confidence_threshold=confidence_threshold,
        )

    def EPISTEMIC_KIND(self, token):
        return str(token)

    def epistemic_args(self, *args):
        enum_values = []
        params = {}
        for arg in args:
            if isinstance(arg, tuple):
                params[arg[0]] = arg[1]
            elif isinstance(arg, str):
                enum_values.append(arg)
        return {"enum_values": enum_values, "params": params}

    def epistemic_arg(self, *parts):
        if len(parts) == 2:
            key, value = parts
            # v0.3: distribution_ref returns a dict
            if isinstance(value, dict):
                return (str(key), value)
            return (str(key), _parse_literal(value))
        return str(parts[0])

    # --- v0.3: Distribution (prior) ---
    def distribution_ref(self, entries):
        return dict(entries)

    def distribution_entries(self, *entries):
        return list(entries)

    def distribution_entry(self, name, value):
        return (str(name), float(value))

    # --- Guard ---
    def guard(self, name, body):
        return Guard(name=str(name), **body)

    def guard_body(self, condition_expr):
        return condition_expr

    def condition_expr(self, *parts):
        conditions = []
        logic = "&&"
        for part in parts:
            if isinstance(part, Condition):
                conditions.append(part)
            elif str(part) in ("&&", "||"):
                logic = str(part)
        return {"conditions": conditions, "logic": logic}

    def condition_term(self, left, comparator=None, right=None):
        if comparator is None:
            return Condition(left=str(left), operator="exists", right="true")
        return Condition(
            left=str(left),
            operator=str(comparator),
            right=_parse_literal(right),
        )

    def COMPARATOR(self, token):
        return str(token)

    # --- Pulse ---
    def pulse(self, name, body):
        return Pulse(name=str(name), **body)

    def pulse_body(self, *parts):
        result = {}
        for part in parts:
            if isinstance(part, dict):
                result.update(part)
        return result

    def pulse_input(self, name):
        return {"input_entity": str(name)}

    def pulse_protect(self, ref):
        return {"guard_ref": str(ref)}

    def pulse_process(self, *steps):
        return {"process_steps": list(steps)}

    def pulse_output(self, ref):
        return {"output_ref": str(ref)}

    def process_step(self, ai_call):
        return ai_call

    # --- v0.3: Trace ---
    def pulse_traces(self, *traces):
        return {"traces": list(traces)}

    def trace(self, name, body):
        return TraceStep(name=str(name), **body)

    def trace_body(self, ai_call, *parts):
        result: dict = {"ai_call": ai_call, "expose": [], "checkpoint": None}
        for part in parts:
            if isinstance(part, dict):
                result.update(part)
        return result

    def trace_expose(self, *idents):
        return {"expose": [str(n) for n in idents]}

    def trace_checkpoint(self, strategy, params_data=None):
        params: dict = {}
        if isinstance(params_data, dict):
            params = params_data.get("args", {})
        return {"checkpoint": CheckpointConfig(strategy=str(strategy), params=params)}

    def CHECKPOINT_STRATEGY(self, token):
        return str(token)

    # --- AI calls ---
    def ai_call(self, func, args_data):
        func_str = str(func)
        args = {}
        prompt_file = None
        fallback = None
        on_low_confidence = None

        if isinstance(args_data, dict):
            args = args_data.get("args", {})
            prompt_file = args_data.get("prompt_file")
            fallback = args_data.get("fallback")
            on_low_confidence = args_data.get("on_low_confidence")  # v0.3

        return AICall(
            function=func_str,
            args=args,
            prompt_file=prompt_file,
            fallback=fallback,
            on_low_confidence=on_low_confidence,
        )

    def AI_FUNC(self, token):
        return str(token)

    def ai_call_args(self, *args):
        result = {"args": {}}
        for arg in args:
            if isinstance(arg, tuple):
                key, value = arg
                if key == "__prompt_file":
                    result["prompt_file"] = value
                elif key == "__fallback":
                    result["fallback"] = value
                elif key == "__checkpoint":  # v0.3
                    result["on_low_confidence"] = value
                else:
                    result["args"][key] = value
        return result

    def ai_call_arg(self, key, value):
        # file_ref and fallback_ref return special tuples ("__prompt_file", ...) / ("__fallback", ...)
        if isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], str) and value[0].startswith("__"):
            return value
        return (str(key), value)

    def ai_call_value(self, value):
        # Handle Fallback.Strategy parsed as dotted_name (without params)
        if isinstance(value, str) and value.startswith("Fallback."):
            strategy = value.split(".", 1)[1]
            fb = FallbackConfig(strategy=strategy, params={})
            return ("__fallback", fb)
        return value

    def file_ref(self, path):
        return ("__prompt_file", _strip_quotes(str(path)))

    def fallback_ref(self, strategy, params=None):
        fb = FallbackConfig(
            strategy=str(strategy),
            params=params if isinstance(params, dict) else {},
        )
        return ("__fallback", fb)

    def FALLBACK_STRATEGY(self, token):
        return str(token)

    def fallback_params(self, args_data):
        if isinstance(args_data, dict):
            return args_data.get("args", {})
        return {}

    # --- v0.3: Checkpoint reference ---
    def checkpoint_ref(self, strategy, params=None):
        cp = CheckpointConfig(
            strategy=str(strategy),
            params=params if isinstance(params, dict) else {},
        )
        return ("__checkpoint", cp)

    def checkpoint_params(self, args_data):
        if isinstance(args_data, dict):
            return args_data.get("args", {})
        return {}

    # --- Pipeline ---
    def pipeline(self, name, body):
        return Pipeline(name=str(name), **body)

    def pipeline_body(self, *parts):
        result = {}
        for part in parts:
            if isinstance(part, dict):
                result.update(part)
        return result

    def pipeline_flow(self, *names):
        return {"flow": [str(n) for n in names]}

    def pipeline_error(self, strategy):
        return {"on_error": strategy}

    def error_strategy(self, *parts):
        if len(parts) == 1:
            if isinstance(parts[0], str):
                return ErrorStrategy(strategy=parts[0])
            if isinstance(parts[0], dict):
                # Retry(args) — name is "Retry" from grammar literal
                return ErrorStrategy(strategy="Retry", params=parts[0].get("args", {}))
        if len(parts) >= 2:
            strategy_name = str(parts[0])
            params = parts[1] if isinstance(parts[1], dict) else {}
            return ErrorStrategy(strategy=strategy_name, params=params.get("args", params))
        return ErrorStrategy(strategy="unknown")

    # --- Lens ---
    def lens(self, name, body):
        return Lens(name=str(name), **body)

    def lens_body(self, *parts):
        result = {}
        for part in parts:
            if isinstance(part, dict):
                result.update(part)
        return result

    def lens_mood(self, value):
        return {"mood": _strip_quotes(str(value))}

    def lens_display(self, *items):
        return {"display": list(items)}

    def lens_inject(self, value):
        return {"inject": _strip_quotes(str(value))}

    def display_item(self, widget, chain=None):
        if chain is not None:
            if isinstance(chain, Widget):
                widget.chain = chain
            elif isinstance(chain, WidgetTrigger):
                widget.trigger = chain
        return widget

    def chain_action(self, target, trig=None):
        if isinstance(target, Widget):
            if trig is not None:
                target.trigger = trig
            return target
        if isinstance(target, WidgetTrigger):
            return target
        return target

    def trigger(self, name):
        return WidgetTrigger(pulse_name=str(name))

    def widget_call(self, widget_type, *args_parts):
        wtype = str(widget_type)
        args = {}
        trigger = None
        for part in args_parts:
            if isinstance(part, dict):
                args.update(part)
            elif isinstance(part, WidgetTrigger):
                trigger = part

        # Resolve positional args based on widget type
        positional = args.pop("_positional", [])
        if wtype == "Button":
            # Button("Label") — first positional is the label
            if positional:
                args["label"] = positional[0]
        else:
            # Table(Entity, ...), Form(Entity, ...) — first positional is entity
            if positional:
                args["entity"] = positional[0]

        return Widget(widget_type=wtype, args=args, trigger=trigger)

    def WIDGET_TYPE(self, token):
        return str(token)

    def widget_args(self, *args):
        result = {}
        positional = []
        for arg in args:
            if isinstance(arg, tuple):
                result[arg[0]] = arg[1]
            elif isinstance(arg, str):
                positional.append(arg)
        if positional:
            result["_positional"] = positional
        return result

    def widget_arg(self, *parts):
        if len(parts) == 1:
            val = parts[0]
            return _strip_quotes(str(val)) if isinstance(val, str) else val
        return (str(parts[0]), parts[1])

    def widget_arg_value(self, value):
        return value

    def widget_arg_list(self, *items):
        return list(items)

    def widget_arg_list_item(self, item):
        return _strip_quotes(str(item))

    # --- Shared ---
    def dotted_name(self, *parts):
        return ".".join(str(p) for p in parts)

    def type_or_ref(self, *parts):
        return ".".join(str(p) for p in parts)

    def literal(self, value):
        return _parse_literal(value)

    def BOOL(self, token):
        return str(token)

    def NULL(self, token):
        return str(token)

    def IDENT(self, token):
        return str(token)

    def NUMBER(self, token):
        s = str(token)
        return float(s) if "." in s else int(s)

    def ESCAPED_STRING(self, token):
        return str(token)


def _strip_quotes(s: str) -> str:
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s


def _parse_literal(value) -> str | int | float | bool | None:
    if isinstance(value, (int, float)):
        return value
    s = str(value)
    if s == "true":
        return True
    if s == "false":
        return False
    if s == "null":
        return None
    return _strip_quotes(s)


def parse_epi(source: str) -> EpiProgram:
    """Parse .epi source code into a typed AST."""
    parser = _get_parser()
    tree = parser.parse(source)
    transformer = EpiTransformer()
    return transformer.transform(tree)


def parse_epi_to_json(source: str, indent: int = 2) -> str:
    """Parse .epi source and return AST as JSON string."""
    program = parse_epi(source)
    return json.dumps(program.model_dump(), indent=indent, ensure_ascii=False)
