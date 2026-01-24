# Contributing to AWS Automation (aa)

Thank you for your interest in contributing to AWS Automation! This document provides guidelines for contributing to the project.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- AWS CLI configured with at least one profile

### Development Setup

```bash
# Clone the repository
git clone https://github.com/expeor/aws-automation.git
cd aws-automation

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pip install pre-commit
pre-commit install
pre-commit install --hook-type commit-msg
```

## Code Style

### Linting & Formatting

This project uses [Ruff](https://github.com/astral-sh/ruff) for linting and formatting:

```bash
# Check for issues
ruff check cli core plugins

# Auto-fix issues
ruff check --fix cli core plugins

# Format code
ruff format cli core plugins
```

### Type Checking

```bash
# Run mypy
mypy cli core --ignore-missing-imports
```

### Style Rules

- Line length: 120 characters
- Quotes: double quotes (`"`)
- Imports: isort style (handled by ruff)
- Type hints: Python 3.10+ style (`list[str]` not `List[str]`)
- Korean docstrings are allowed

## Commit Conventions

We follow [Conventional Commits](https://www.conventionalcommits.org/). This enables automatic changelog generation and semantic versioning.

### Commit Message Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type | Description | Example |
|------|-------------|---------|
| `feat` | New feature | New tool, new functionality |
| `fix` | Bug fix | Error fix, exception handling |
| `refactor` | Code refactoring | No behavior change |
| `docs` | Documentation | README, docstrings |
| `test` | Tests | Add/modify tests |
| `chore` | Maintenance | Build, dependencies |
| `style` | Code style | Formatting only |
| `perf` | Performance | Performance improvements |
| `ci` | CI/CD | GitHub Actions, workflows |

### Scopes

| Scope | Description |
|-------|-------------|
| `cli` | CLI module |
| `core` | Core module |
| `plugins` | Plugins |
| `deps` | Dependencies |
| Service name | Specific AWS service (ec2, vpc, iam, etc.) |

### Examples

```bash
# Feature
feat(plugins): add elasticache unused cluster detection

# Bug fix
fix(core): handle SSO token expiration gracefully

# Refactoring
refactor(cli): simplify menu navigation logic

# Documentation
docs: update README with new CLI options

# Breaking change
feat(cli)!: change run command arguments

BREAKING CHANGE: -p flag now requires profile name instead of index
```

## Branch Naming

```
<type>/<description>
```

| Type | Use case | Example |
|------|----------|---------|
| `feat/` | New feature | `feat/elasticache-unused` |
| `fix/` | Bug fix | `fix/sso-token-refresh` |
| `refactor/` | Refactoring | `refactor/parallel-execution` |
| `docs/` | Documentation | `docs/update-readme` |
| `test/` | Tests | `test/add-moto-tests` |
| `chore/` | Maintenance | `chore/upgrade-deps` |

## Pull Request Process

1. **Create a branch** following the naming convention
2. **Make your changes** with appropriate commits
3. **Run tests locally**:
   ```bash
   pytest tests/ -v
   ```
4. **Run linting**:
   ```bash
   ruff check cli core plugins
   ruff format --check cli core plugins
   ```
5. **Push and create a PR** with a descriptive title following commit conventions
6. **Fill out the PR template** completely
7. **Wait for CI** to pass
8. **Address review feedback** if any

### PR Title Format

PR titles must follow Conventional Commits format:

```
feat(plugins): add RDS snapshot audit tool
fix(core): handle pagination correctly
docs: update installation guide
```

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific module tests
pytest tests/core/ -v
pytest tests/plugins/ec2/ -v

# Run with coverage
pytest tests/ --cov=cli --cov=core --cov=plugins
```

### Writing Tests

- Use `pytest` for all tests
- Use `moto` for AWS service mocking
- Follow the existing test structure in `tests/`

## Adding a New Plugin Tool

See [CLAUDE.md](CLAUDE.md) for detailed plugin development patterns.

### Quick Reference

1. Create module in `plugins/{service}/{tool_name}.py`
2. Add tool entry to `plugins/{service}/__init__.py`
3. Implement `run(ctx)` function
4. Add tests in `tests/plugins/{service}/`

## Issue Guidelines

### Before Creating an Issue

1. Search existing issues to avoid duplicates
2. Check the documentation for answers
3. Gather relevant information (error messages, versions, etc.)

### Creating a Good Issue

- Use a clear, descriptive title
- Fill out the issue template completely
- Include steps to reproduce (for bugs)
- Provide context and motivation (for features)

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow
- Follow the project's coding standards

## Questions?

If you have questions, feel free to:
- Open an issue with the "question" label
- Check existing issues and discussions

Thank you for contributing!
