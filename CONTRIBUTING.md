# Contributing to Epi

Thank you for your interest in contributing to Epi.

Epi is in **active research stage (v0.2)**. Contributions are welcome, but please read the guidelines below before submitting.

## How to Contribute

### Reporting Issues

- Use [GitHub Issues](https://github.com/RandMelville/epi-lang/issues) to report bugs or suggest features.
- Include the `.epi` source file that triggers the issue, if applicable.
- Include the full error output.

### Submitting Changes

1. Fork the repository.
2. Create a feature branch from `main`.
3. Make your changes with clear, descriptive commits.
4. Ensure the parser still validates the canonical example:
   ```bash
   epi validate examples/contrato.epi
   ```
5. Open a Pull Request with a description of what changed and why.

### Areas Where Help is Needed

- **Grammar edge cases** — test the Lark parser with new `.epi` files and report failures.
- **New generator targets** — FastAPI, Django, SvelteKit, etc.
- **Examples** — write `.epi` files for different domains (healthcare, fintech, edtech).
- **Tests** — pytest coverage for parser, transformer, and generators.

## Development Setup

```bash
git clone https://github.com/RandMelville/epi-lang.git
cd epi-lang
pip install -e ".[dev]"
epi validate examples/contrato.epi
```

## Code of Conduct

Be respectful. Be constructive. Focus on the work.

## License

By contributing, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).
