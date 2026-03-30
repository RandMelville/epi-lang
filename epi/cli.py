"""
Epi CLI — Epistemic Transpiler Command Line Interface

Usage:
    epi parse <file.epi>                   → Print AST as JSON
    epi transpile <file.epi> --target X    → Generate project files
    epi validate <file.epi>                → Validate syntax only
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from epi import __version__
from epi.parser.builder import parse_epi, parse_epi_to_json
from epi.parser.ast_nodes import TypeDomain

app = typer.Typer(
    name="epi",
    help="Epi — Epistemic Programming Interface v0.3\nTranspile .epi files into full-stack projects.",
    add_completion=False,
)
console = Console()


@app.callback()
def main():
    """Epi — The Epistemic Transpiler."""
    pass


@app.command()
def version():
    """Show Epi version."""
    console.print(f"[bold]Epi[/bold] v{__version__}")


@app.command()
def parse(
    file: Path = typer.Argument(..., help="Path to .epi file"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output JSON file (default: stdout)"),
    pretty: bool = typer.Option(True, "--pretty/--compact", help="Pretty-print JSON"),
):
    """Parse a .epi file and output its AST as JSON."""
    source = _read_source(file)
    try:
        ast_json = parse_epi_to_json(source, indent=2 if pretty else None)
    except Exception as e:
        console.print(f"[red]Parse error:[/red] {e}")
        raise typer.Exit(1)

    if output:
        output.write_text(ast_json)
        console.print(f"[green]AST written to {output}[/green]")
    else:
        syntax = Syntax(ast_json, "json", theme="monokai")
        console.print(syntax)


@app.command()
def validate(
    file: Path = typer.Argument(..., help="Path to .epi file"),
):
    """Validate .epi syntax without generating code."""
    source = _read_source(file)
    try:
        program = parse_epi(source)
    except Exception as e:
        console.print(f"[red]Validation failed:[/red] {e}")
        raise typer.Exit(1)

    # Show summary
    table = Table(title=f"[bold]{file.name}[/bold] — Valid")
    table.add_column("Primitive", style="cyan")
    table.add_column("Count", style="green")
    table.add_column("Names")

    table.add_row("Entity", str(len(program.entities)), ", ".join(e.name for e in program.entities))
    table.add_row("Guard", str(len(program.guards)), ", ".join(g.name for g in program.guards))
    table.add_row("Pulse", str(len(program.pulses)), ", ".join(p.name for p in program.pulses))
    table.add_row("Pipeline", str(len(program.pipelines)), ", ".join(p.name for p in program.pipelines))
    table.add_row("Lens", str(len(program.lenses)), ", ".join(l.name for l in program.lenses))

    # Count epistemic vs rigid fields
    rigid = sum(
        1 for e in program.entities for f in e.fields if f.type.domain == TypeDomain.RIGID
    )
    epistemic = sum(
        1 for e in program.entities for f in e.fields if f.type.domain == TypeDomain.EPISTEMIC
    )

    console.print(table)
    console.print(
        Panel(
            f"[bold]Epistemic Analysis:[/bold]\n"
            f"  Rigid fields: [green]{rigid}[/green] (deterministic → templates)\n"
            f"  Epistemic fields: [yellow]{epistemic}[/yellow] (AI-inferred → LLM generation)",
            title="Type System",
        )
    )


@app.command()
def transpile(
    file: Path = typer.Argument(..., help="Path to .epi file"),
    target: str = typer.Option("nextjs", "--target", "-t", help="Target framework: nextjs, fastapi"),
    outdir: Path = typer.Option(Path("./output"), "--outdir", "-d", help="Output directory"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be generated without writing"),
):
    """Transpile a .epi file into a full-stack project."""
    from epi.generators.deterministic.prisma import generate_prisma
    from epi.generators.deterministic.middleware import generate_middleware
    from epi.generators.deterministic.routes import generate_routes
    from epi.generators.deterministic.validators import generate_validators
    from epi.generators.epistemic.ai_scan import generate_pulse_stub
    from epi.generators.epistemic.lens_mood import generate_lens_stub
    from epi.generators.epistemic.traces import generate_all_traces
    from epi.generators.scaffold import (
        generate_package_json,
        generate_tsconfig,
        generate_next_config,
        generate_env_example,
        generate_gitignore,
        generate_readme,
    )

    source = _read_source(file)
    try:
        program = parse_epi(source)
    except Exception as e:
        console.print(f"[red]Parse error:[/red] {e}")
        raise typer.Exit(1)

    files_to_write: dict[str, str] = {}

    # Deterministic layer
    if program.entities:
        files_to_write["prisma/schema.prisma"] = generate_prisma(program)

    middleware_files = generate_middleware(program, target)
    files_to_write.update(middleware_files)

    route_files = generate_routes(program, target)
    files_to_write.update(route_files)

    # Validators (epistemic boundary enforcement)
    validator_files = generate_validators(program)
    files_to_write.update(validator_files)

    # Epistemic layer (stubs)
    for pulse in program.pulses:
        stub = generate_pulse_stub(pulse, program, target)
        fname = f"pulses/{_to_kebab(pulse.name)}.{'ts' if target == 'nextjs' else 'py'}"
        files_to_write[fname] = stub

    for lens in program.lenses:
        stub = generate_lens_stub(lens, target)
        fname = f"components/{_to_kebab(lens.name)}.tsx"
        files_to_write[fname] = stub

    # v0.3: Trace infrastructure (inspect/resume routes + store)
    trace_files = generate_all_traces(program)
    files_to_write.update(trace_files)

    # Scaffold: project configuration files
    if target == "nextjs":
        files_to_write["package.json"] = generate_package_json(program)
        files_to_write["tsconfig.json"] = generate_tsconfig()
        files_to_write["next.config.js"] = generate_next_config()
    files_to_write[".env.example"] = generate_env_example()
    files_to_write[".gitignore"] = generate_gitignore()
    files_to_write["README.md"] = generate_readme(program, target)

    # Prompt files: copy referenced prompts to output/prompts/
    prompt_names = _collect_prompt_files(program)
    prompts_src = _find_prompts_dir(file)
    for prompt_name in sorted(prompt_names):
        if prompts_src:
            src = prompts_src / prompt_name
            if src.exists():
                files_to_write[f"prompts/{prompt_name}"] = src.read_text()
            else:
                console.print(f"  [yellow]warning[/yellow] prompt not found: {src}")
        else:
            console.print(f"  [yellow]warning[/yellow] prompts/ directory not found — {prompt_name} will be missing")

    # Detect Anthropic usage for setup warning
    uses_anthropic = any("Anthropic" in content for content in files_to_write.values())

    # Output
    if dry_run:
        console.print(Panel("[bold]Dry run — files that would be generated:[/bold]"))
        for filepath, content in files_to_write.items():
            console.print(f"\n[cyan]{filepath}[/cyan]")
            console.print(Syntax(content[:500], _guess_lang(filepath), theme="monokai"))
    else:
        for filepath, content in files_to_write.items():
            full_path = outdir / filepath
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
            console.print(f"  [green]wrote[/green] {filepath}")

        next_steps = (
            "  1. cd " + str(outdir) + "\n"
            "  2. npm install\n"
            "  3. cp .env.example .env\n"
            "  4. Edit .env — set DATABASE_URL and ANTHROPIC_API_KEY\n"
            "  5. npx prisma migrate dev --name init\n"
            "  6. npm run dev"
        )
        if not uses_anthropic:
            next_steps = next_steps.replace("  4. Edit .env — set DATABASE_URL and ANTHROPIC_API_KEY\n", "  4. Edit .env — set DATABASE_URL\n")

        console.print(
            Panel(
                f"[bold green]Transpilation complete![/bold green]\n"
                f"  Target: {target}\n"
                f"  Files: {len(files_to_write)}\n"
                f"  Output: {outdir.resolve()}\n\n"
                f"[bold]Next steps:[/bold]\n{next_steps}",
                title="Epi Transpiler",
            )
        )

        if uses_anthropic:
            console.print(
                Panel(
                    "[bold yellow]ANTHROPIC_API_KEY required[/bold yellow]\n\n"
                    "This project calls the Claude API. Before running:\n"
                    "  • Get your key at [link]https://console.anthropic.com/keys[/link]\n"
                    "  • Add to .env: ANTHROPIC_API_KEY=sk-ant-...",
                    title="Setup",
                )
            )


def _collect_prompt_files(program) -> set[str]:
    """Return set of prompt filenames (without @prompts/ prefix) referenced by all Pulses."""
    names: set[str] = set()
    for pulse in program.pulses:
        for step in pulse.process_steps:
            if step.prompt_file:
                names.add(step.prompt_file.replace("@prompts/", ""))
        for trace in pulse.traces:
            if trace.ai_call.prompt_file:
                names.add(trace.ai_call.prompt_file.replace("@prompts/", ""))
    return names


def _find_prompts_dir(source_file: Path) -> Path | None:
    """Locate the prompts/ directory: first next to the source file, then in CWD."""
    candidates = [
        source_file.parent / "prompts",
        Path.cwd() / "prompts",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def _read_source(file: Path) -> str:
    if not file.exists():
        console.print(f"[red]File not found:[/red] {file}")
        raise typer.Exit(1)
    if file.suffix != ".epi":
        console.print(f"[yellow]Warning:[/yellow] File does not have .epi extension")
    return file.read_text()


def _to_kebab(name: str) -> str:
    parts = []
    current = ""
    for ch in name:
        if ch.isupper() and current:
            parts.append(current)
            current = ch
        else:
            current += ch
    if current:
        parts.append(current)
    return "-".join(p.lower() for p in parts)


def _guess_lang(filepath: str) -> str:
    if filepath.endswith(".ts") or filepath.endswith(".tsx"):
        return "typescript"
    if filepath.endswith(".py"):
        return "python"
    if filepath.endswith(".prisma"):
        return "graphql"
    return "text"


if __name__ == "__main__":
    app()
