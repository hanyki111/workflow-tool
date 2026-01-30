# AI Workflow Engine

> **AI-Native Workflow Management System** - A structured development workflow engine designed for AI-assisted software development.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Commands Reference](#commands-reference)
- [Workflow Concepts](#workflow-concepts)
- [Tutorial](#tutorial)
- [Examples](#examples)
- [Advanced Usage](#advanced-usage)
- [Internationalization](#internationalization)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Overview

The AI Workflow Engine is a command-line tool that enforces structured development workflows. It's specifically designed to work with AI assistants (like Claude, GPT, etc.) to maintain discipline and consistency throughout the software development lifecycle.

### Why Use This Tool?

When working with AI assistants on complex projects, several challenges arise:

1. **Context Loss**: AI assistants may forget project state between sessions
2. **Process Skipping**: Critical steps like reviews and testing get overlooked
3. **Documentation Drift**: Specs and docs become outdated
4. **Technical Debt**: Issues accumulate without tracking

The AI Workflow Engine solves these by:

- **Enforcing Stage-Based Workflows**: Each stage has mandatory checklists
- **Providing State Awareness**: AI can read current workflow state
- **Requiring Explicit Transitions**: Can't skip stages without completing requirements
- **Logging All Actions**: Complete audit trail of the development process

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI (flow)                           │
├─────────────────────────────────────────────────────────────┤
│  Commands: status | next | check | set | review | tutorial  │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                      Core Engine                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Controller  │  │    State    │  │      Loader         │  │
│  │ (Workflow   │  │ (JSON       │  │ (YAML config        │  │
│  │  logic)     │  │  persist)   │  │  parsing)           │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                      Plugin Layer                            │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │ FileExistsValidator│ │ CommandValidator │  [Custom...]   │
│  └──────────────────┘  └──────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Features

### Core Features

| Feature | Description |
|---------|-------------|
| **Stage-Based Workflow** | Define stages (M0-M4, P1-P7) with checklists and transition rules |
| **Enforced Transitions** | Cannot advance without completing all checklist items |
| **Plugin System** | Extensible validators for custom conditions |
| **State Persistence** | JSON-based state tracking across sessions |
| **Audit Logging** | All actions are logged for accountability |

### AI Integration Features

| Feature | Description |
|---------|-------------|
| **Status Command** | AI can query current state at session start |
| **USER-APPROVE** | Certain actions require human verification |
| **Sub-Agent Reviews** | Record and track AI sub-agent reviews |
| **Evidence Tracking** | Attach justifications to completed items |

### Developer Experience

| Feature | Description |
|---------|-------------|
| **Bilingual Support** | Full Korean/English i18n |
| **Interactive Tutorial** | Built-in learning system |
| **Shell Alias** | Easy `flow` command setup |
| **YAML Configuration** | Human-readable workflow definitions |

---

## Quick Start

### 30-Second Setup

```bash
# 1. Clone and install
git clone https://github.com/your-org/workflow-tool.git
cd workflow-tool
pip install -e .

# 2. Check it works
flow --help

# 3. See current status
flow status

# 4. Start the tutorial
flow tutorial
```

### Minimal Workflow Example

Create `workflow.yaml`:

```yaml
version: "2.0"

stages:
  START:
    id: "START"
    label: "Project Start"
    checklist:
      - "Define project goals"
      - "Set up development environment"
    transitions:
      - target: "DEVELOP"

  DEVELOP:
    id: "DEVELOP"
    label: "Development"
    checklist:
      - "Write code"
      - "Write tests"
      - "Run tests"
    transitions:
      - target: "REVIEW"

  REVIEW:
    id: "REVIEW"
    label: "Review"
    checklist:
      - "Code review completed"
      - "[USER-APPROVE] Approve for merge"
    transitions:
      - target: "DONE"

  DONE:
    id: "DONE"
    label: "Complete"
    checklist:
      - "Merge to main"
      - "Update documentation"
```

Create `.workflow/state.json`:

```json
{
  "current_stage": "START",
  "checklist": []
}
```

Now use it:

```bash
flow status           # See current stage
flow check 1 2        # Mark items as done
flow next             # Move to next stage
```

---

## Installation

### Requirements

- Python 3.10 or higher
- pip (Python package manager)

### Method 1: Install from Source (Recommended for Development)

```bash
# Clone the repository
git clone https://github.com/your-org/workflow-tool.git
cd workflow-tool

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode
pip install -e .

# Verify installation
flow --help
```

### Method 2: Install from Package

```bash
pip install ai-workflow-engine
```

### Method 3: Run Without Installing

```bash
# Direct execution
python -m workflow --help

# Or set up an alias
alias flow='python -m workflow'
```

### Shell Alias Setup

For convenient access, install a shell alias:

```bash
# Automatic installation
flow install-alias --name flow

# Or manually add to ~/.bashrc or ~/.zshrc:
alias flow='python -m workflow'

# Reload shell config
source ~/.bashrc  # or ~/.zshrc
```

### Verify Installation

```bash
# Should display version and help
flow --help

# Should show "Workflow Management Tool"
python -m workflow --help
```

---

## Configuration

### File Structure

A typical project using workflow-tool:

```
my-project/
├── workflow.yaml           # Workflow definition (required)
├── .workflow/
│   ├── state.json          # Current state (auto-created)
│   ├── secret              # Secret hash for USER-APPROVE (gitignored)
│   └── audit.log           # Action audit log (gitignored)
├── .memory/                # Project knowledge (optional)
│   ├── docs/
│   │   └── PROJECT_MANAGEMENT_GUIDE.md
│   └── modules/
│       └── [feature-name]/
│           ├── spec.md
│           └── current.md
└── ... (your project files)
```

### workflow.yaml Reference

Complete configuration reference:

```yaml
# Version (required)
version: "2.0"

# Global variables (optional)
variables:
  project_name: "my-project"
  test_command: "pytest -v"

# Plugin registration (optional)
plugins:
  fs: "workflow.plugins.fs.FileExistsValidator"
  shell: "workflow.plugins.shell.CommandValidator"

# Reusable condition sets (optional)
rulesets:
  all_checked:
    - rule: all_checked
      fail_message: "Complete all checklist items first"

  tests_pass:
    - rule: shell
      args:
        cmd: "pytest"
        expect_code: 0
      fail_message: "Tests must pass"

# Stage definitions (required)
stages:
  M0:
    id: "M0"                          # Unique identifier
    label: "Tech Debt Review"         # Human-readable name
    checklist:                        # Items to complete
      - "Review existing tech debt"
      - "Prioritize debt items"
      - "[USER-APPROVE] Approve debt plan"  # Requires token
    transitions:                      # Where can we go from here?
      - target: "M1"
        conditions:
          - use_ruleset: all_checked  # Reference a ruleset
          - rule: fs                  # Or use a plugin directly
            args:
              path: "docs/debt-plan.md"
    on_enter:                         # Actions on stage entry (optional)
      - action: "log"
        args:
          message: "Starting tech debt review"

  M1:
    id: "M1"
    label: "Planning"
    # ... more stages
```

### State File Format

`.workflow/state.json`:

```json
{
  "current_milestone": "M1",
  "current_phase": "1.2",
  "current_stage": "P3",
  "active_module": "inventory-system",
  "checklist": [
    {
      "text": "Write unit tests",
      "checked": true,
      "evidence": "All 15 tests passing",
      "required_agent": null
    },
    {
      "text": "[USER-APPROVE] Deploy to staging",
      "checked": false,
      "evidence": null,
      "required_agent": null
    }
  ]
}
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLOW_LANG` | Display language (`en`, `ko`) | System locale |

---

## Commands Reference

### `flow status`

Display current workflow state.

```bash
# Full status display
flow status

# Output:
# Current Stage: M0 (Tech Debt Review)
# ========================================
# Active Module: core-engine
# ----------------------------------------
# 1. [x] Review existing tech debt
# 2. [x] Prioritize debt items
# 3. [ ] [USER-APPROVE] Approve debt plan

# Compact one-line format
flow status --oneline
# Output: M0 (Tech Debt Review) - 2/3
```

### `flow check`

Mark checklist items as completed.

```bash
# Check single item (1-based index)
flow check 1

# Check multiple items
flow check 1 2 3

# Add evidence/justification
flow check 1 --evidence "Reviewed with team on 2024-01-15"

# Check USER-APPROVE item with token
flow check 3 --token "your-secret-phrase"

# Check with both
flow check 3 --token "secret" --evidence "Approved by @alice after security review"
```

### `flow next`

Transition to the next stage.

```bash
# Auto-detect next stage (uses first valid transition)
flow next

# Specify target stage explicitly
flow next M1

# Force transition (bypasses all conditions)
flow next --force --reason "Emergency hotfix required"

# Possible outputs:
# Success: "Transitioned to M1: Planning"
# Blocked: "Cannot transition: All checklist items must be completed"
```

### `flow set`

Manually set current stage or module.

```bash
# Set stage only
flow set M2

# Set stage and active module
flow set P3 --module inventory-system

# Useful for:
# - Resuming after state corruption
# - Jumping to a specific point
# - Testing specific stages
```

### `flow review`

Record sub-agent review results.

```bash
flow review --agent "code-reviewer" --summary "All SOLID principles followed, no blocking issues found"

# This creates an audit log entry that can be verified later
```

### `flow secret-generate`

Create a secret for USER-APPROVE items.

```bash
flow secret-generate

# Interactive prompts:
# Enter your secret phrase: ********
# Confirm secret phrase: ********
# Secret hash saved to .workflow/secret
```

### `flow tutorial`

Access the built-in tutorial system.

```bash
# List all sections
flow tutorial --list

# View specific section
flow tutorial --section 0

# Start interactive tutorial
flow tutorial

# Use alias
flow guide --section 2
```

### `flow install-alias`

Install shell alias for easier access.

```bash
# Install with default name 'flow'
flow install-alias

# Install with custom name
flow install-alias --name wf
```

### Global Options

```bash
# Set display language
flow --lang ko status
flow --lang en --help

# Get help
flow --help
flow status --help
```

---

## Workflow Concepts

### Stage Types

The workflow engine supports two levels of stages:

#### Milestone Stages (M0-M4)

High-level project phases that span days to weeks:

| Stage | Name | Purpose |
|-------|------|---------|
| M0 | Tech Debt Review | Assess and plan technical debt |
| M1 | Milestone Planning | Create PRD, define scope |
| M2 | Milestone Discussion | Architecture review, user approval |
| M3 | Branch Creation | Git setup for the milestone |
| M4 | Milestone Closing | Merge, document, celebrate |

#### Phase Stages (P1-P7)

Detailed implementation steps within each milestone:

| Stage | Name | Purpose |
|-------|------|---------|
| P1 | Phase Planning | Define specific deliverables |
| P2 | Phase Discussion | Technical approach, user approval |
| P3 | Spec | Write technical specification |
| P4 | Implementation | Write the code |
| P5 | Testing | Unit and integration tests |
| P6 | Self-Review | Code quality check |
| P7 | Phase Closing | Documentation sync, commit |

### Workflow Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    MILESTONE LIFECYCLE                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─ [Milestone Start] ────────────────────────────────────┐ │
│  │  M0: Tech Debt Review                                  │ │
│  │  M1: Milestone Planning                                │ │
│  │  M2: Milestone Discussion                              │ │
│  │  M3: Branch Creation                                   │ │
│  └────────────────────────────────────────────────────────┘ │
│                            │                                 │
│                            ▼                                 │
│  ┌─ [Phase Loop] ─────────────────────────────────────────┐ │
│  │                                                         │ │
│  │   Phase 1 ──► Phase 2 ──► Phase 3 ──► ...              │ │
│  │      │           │           │                          │ │
│  │      └───────────┴───────────┴──────────┐              │ │
│  │                                          │              │ │
│  │   For each phase:                        │              │ │
│  │   P1 → P2 → P3 → P4 → P5 → P6 → P7 ─────┘              │ │
│  │                                                         │ │
│  └─────────────────────────────────────────────────────────┘ │
│                            │                                 │
│                            ▼                                 │
│  ┌─ [Milestone End] ──────────────────────────────────────┐ │
│  │  M4: Milestone Closing                                 │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Checklists

Each stage has a checklist of items that must be completed:

```yaml
checklist:
  - "Regular item - just check when done"
  - "[USER-APPROVE] Requires human verification with token"
  - "[AGENT:spec-validator] Requires sub-agent review"
```

**Checklist Item Types:**

| Type | Syntax | Description |
|------|--------|-------------|
| Regular | `"Item text"` | AI can check freely |
| User Approve | `"[USER-APPROVE] Text"` | Requires secret token |
| Agent Review | `"[AGENT:name] Text"` | Requires sub-agent verification |

### Transitions

Transitions define how to move between stages:

```yaml
transitions:
  - target: "M1"                    # Where to go
    conditions:                     # What must be true
      - use_ruleset: all_checked    # Use predefined ruleset
      - rule: fs                    # Use plugin validator
        args:
          path: "docs/plan.md"
        fail_message: "Plan document must exist"
```

**Transition Rules:**

| Rule | Description |
|------|-------------|
| `all_checked` | All checklist items must be checked |
| `user_approved` | USER-APPROVE items must have valid token |
| `use_ruleset` | Apply a named ruleset |
| Plugin rules | Custom validators (fs, shell, etc.) |

### Plugins

Built-in plugins for transition conditions:

#### FileExistsValidator

```yaml
plugins:
  fs: "workflow.plugins.fs.FileExistsValidator"

# Usage in conditions:
conditions:
  - rule: fs
    args:
      path: "src/main.py"      # File to check
      not_empty: true          # Must have content (optional)
```

#### CommandValidator

```yaml
plugins:
  shell: "workflow.plugins.shell.CommandValidator"

# Usage in conditions:
conditions:
  - rule: shell
    args:
      cmd: "pytest tests/"     # Command to run
      expect_code: 0           # Expected exit code (default: 0)
```

---

## Tutorial

### Built-in Interactive Tutorial

The workflow tool includes a comprehensive built-in tutorial:

```bash
# List all tutorial sections
flow tutorial --list

# Output:
# 0. Introduction
# 1. Installation & Setup
# 2. Basic Commands
# 3. Security & Secrets
# 4. Advanced Features
# 5. Best Practices

# View a specific section
flow tutorial --section 0

# Start interactive mode
flow tutorial
```

### Tutorial Contents

| Section | Topics Covered |
|---------|----------------|
| 0. Introduction | What is workflow-tool, key concepts, quick start |
| 1. Installation | pip install, shell alias, initial configuration |
| 2. Basic Commands | status, check, next, set - with examples |
| 3. Security | USER-APPROVE, secret generation, audit trail |
| 4. Advanced | Custom plugins, rulesets, variables, hooks |
| 5. Best Practices | Design tips, daily workflow, AI collaboration |

### Learning Path

**For New Users:**
1. Run `flow tutorial` to start interactive tutorial
2. Follow sections 0-2 for basics
3. Create a simple workflow for practice
4. Advance to sections 3-5

**For Experienced Users:**
1. Check `flow tutorial --section 4` for advanced features
2. Review examples in `examples/` directory
3. Create custom plugins for your needs

---

## Examples

The `examples/` directory contains ready-to-use workflow configurations:

### Simple Workflow

Location: `examples/simple/`

A minimal 3-stage workflow for small projects:

```bash
cd examples/simple
flow status
```

### Full Project Workflow

Location: `examples/full-project/`

Complete M0-M4, P1-P7 workflow matching PROJECT_MANAGEMENT_GUIDE.md:

```bash
cd examples/full-project
flow status
```

### Custom Plugins Example

Location: `examples/custom-plugins/`

Demonstrates creating and using custom validators:

```bash
cd examples/custom-plugins
flow status
```

See `examples/README.md` for detailed documentation of each example.

---

## Advanced Usage

### Creating Custom Plugins

1. Create a validator class:

```python
# my_project/validators/api_validator.py
from workflow.core.validator import BaseValidator
import requests

class APIHealthValidator(BaseValidator):
    """Check if an API endpoint is healthy."""

    def validate(self, args, context):
        url = args.get('url')
        timeout = args.get('timeout', 5)

        try:
            response = requests.get(url, timeout=timeout)
            return response.status_code == 200
        except:
            return False
```

2. Register in workflow.yaml:

```yaml
plugins:
  api_health: "my_project.validators.api_validator.APIHealthValidator"
```

3. Use in conditions:

```yaml
stages:
  DEPLOY:
    transitions:
      - target: "DONE"
        conditions:
          - rule: api_health
            args:
              url: "https://api.example.com/health"
              timeout: 10
            fail_message: "API health check failed"
```

### Rulesets for Reusability

Define common condition sets once:

```yaml
rulesets:
  production_ready:
    - rule: all_checked
    - rule: shell
      args:
        cmd: "pytest"
    - rule: shell
      args:
        cmd: "mypy src/"
    - rule: fs
      args:
        path: "CHANGELOG.md"
        not_empty: true

stages:
  PRE_DEPLOY:
    transitions:
      - target: "DEPLOY"
        conditions:
          - use_ruleset: production_ready
```

### Variables and Substitution

Use variables for consistency:

```yaml
variables:
  project_name: "my-app"
  test_cmd: "pytest tests/ -v"
  main_branch: "main"

stages:
  TEST:
    checklist:
      - "Run ${test_cmd}"
    transitions:
      - target: "MERGE"
        conditions:
          - rule: shell
            args:
              cmd: "${test_cmd}"
```

### Stage Entry Hooks

Execute actions when entering a stage:

```yaml
stages:
  P4:
    label: "Implementation"
    on_enter:
      - action: "shell"
        args:
          cmd: "git status"
      - action: "log"
        args:
          message: "Starting implementation phase"
```

### Working with AI Assistants

Instruct your AI assistant to follow the workflow:

```markdown
## AI Instructions

Before starting any task:
1. Run `flow status` to check current stage
2. Follow the checklist items in order
3. Check off items as you complete them: `flow check N`
4. Don't proceed to next stage until all items are done
5. Use `flow next` to advance when ready

For USER-APPROVE items:
- Ask the human to run `flow check N --token "..."`
- Wait for confirmation before proceeding
```

### Multi-Project Setup

For organizations with multiple projects:

```
organization/
├── workflow-templates/           # Shared templates
│   ├── standard-workflow.yaml
│   └── hotfix-workflow.yaml
├── project-a/
│   └── workflow.yaml            # Can extend templates
├── project-b/
│   └── workflow.yaml
```

---

## Internationalization

### Supported Languages

| Code | Language | Status |
|------|----------|--------|
| `en` | English | Full support |
| `ko` | Korean (한국어) | Full support |

### Setting Language

```bash
# Via command line flag
flow --lang ko status

# Via environment variable
export FLOW_LANG=ko
flow status

# Language detection priority:
# 1. --lang flag
# 2. FLOW_LANG environment variable
# 3. System locale
# 4. Default (English)
```

### Adding New Languages

1. Create message catalog: `workflow/i18n/messages/{lang}.yaml`
2. Create tutorial content: `workflow/tutorial/content/{lang}/`
3. Test: `flow --lang {lang} --help`

---

## Troubleshooting

### Common Issues

#### "Configuration file not found"

```bash
# Error: Configuration file not found: workflow.yaml

# Solution: Create workflow.yaml in project root
# Or specify path: flow --config path/to/workflow.yaml status
```

#### "Cannot transition" Error

```bash
# Error: Cannot transition: All checklist items must be completed

# Solution: Check remaining items
flow status

# Complete missing items
flow check 3 4

# Try again
flow next
```

#### "Invalid token for USER-APPROVE"

```bash
# Error: Invalid token for USER-APPROVE

# Solution 1: Check if secret is generated
ls .workflow/secret

# Solution 2: Regenerate secret
flow secret-generate

# Solution 3: Use correct phrase
flow check 2 --token "your-actual-secret"
```

#### Plugin Load Errors

```bash
# Error: Failed to load plugin: my_plugin

# Solution: Check plugin path in workflow.yaml
# Ensure the module is importable:
python -c "from my_project.validators import MyValidator"
```

#### State Corruption

```bash
# If state.json is corrupted:

# Option 1: Reset to a known stage
flow set M0

# Option 2: Delete and reinitialize
rm .workflow/state.json
flow status  # Creates fresh state
```

### Debug Mode

For detailed debugging:

```bash
# Set Python debug
PYTHONDEBUG=1 flow status

# Check state file directly
cat .workflow/state.json | python -m json.tool

# Validate YAML config
python -c "import yaml; yaml.safe_load(open('workflow.yaml'))"
```

### Getting Help

1. **Tutorial**: `flow tutorial`
2. **Command Help**: `flow <command> --help`
3. **Documentation**: `.memory/docs/`
4. **Issues**: https://github.com/your-org/workflow-tool/issues

---

## Contributing

### Development Setup

```bash
# Clone repository
git clone https://github.com/your-org/workflow-tool.git
cd workflow-tool

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```

### Project Structure

```
workflow-tool/
├── workflow/                # Main package
│   ├── __init__.py
│   ├── __main__.py         # Entry point
│   ├── cli.py              # CLI commands
│   ├── core/               # Core engine
│   │   ├── controller.py   # Main logic
│   │   ├── state.py        # State management
│   │   ├── schema.py       # Data classes
│   │   ├── validator.py    # Base validator
│   │   ├── loader.py       # Config loading
│   │   └── auth.py         # Authentication
│   ├── plugins/            # Built-in validators
│   ├── i18n/               # Internationalization
│   └── tutorial/           # Tutorial system
├── examples/               # Example workflows
├── tests/                  # Test suite
└── docs/                   # Documentation
```

### Coding Standards

- Python 3.10+ type hints
- PEP 8 style guide
- Docstrings for public APIs
- Tests for new features

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- Inspired by structured development methodologies
- Built for the AI-assisted development era
- Special thanks to all contributors

---

**Happy Workflow Managing!** 🚀
