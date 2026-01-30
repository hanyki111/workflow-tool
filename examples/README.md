# Workflow Examples

This directory contains example workflow configurations demonstrating various use cases and complexity levels.

---

## Directory Structure

```
examples/
├── README.md                    # This file
├── simple/                      # Minimal 3-stage workflow
│   ├── workflow.yaml
│   ├── .workflow/
│   │   └── state.json
│   └── README.md
├── full-project/                # Complete M0-M4, P1-P7 workflow
│   ├── workflow.yaml
│   ├── .workflow/
│   │   └── state.json
│   └── README.md
└── custom-plugins/              # Custom validator examples
    ├── workflow.yaml
    ├── .workflow/
    │   └── state.json
    ├── validators/
    │   └── custom.py
    └── README.md
```

---

## Example Descriptions

### 1. Simple Workflow (`simple/`)

**Best for:** Small projects, learning, quick tasks

A minimal workflow with just 3 stages:
- `START` → `DEVELOP` → `DONE`

Features demonstrated:
- Basic stage definitions
- Simple checklists
- Automatic transitions

**Try it:**
```bash
cd examples/simple
flow status
flow check 1 2
flow next
```

---

### 2. Full Project Workflow (`full-project/`)

**Best for:** Real software projects, team workflows

Complete implementation of the dual-track workflow:

**Milestone Stages:**
- M0: Tech Debt Review
- M1: Milestone Planning
- M2: Milestone Discussion
- M3: Branch Creation
- M4: Milestone Closing

**Phase Stages (repeated for each phase):**
- P1: Phase Planning
- P2: Phase Discussion
- P3: Spec
- P4: Implementation
- P5: Testing
- P6: Self-Review
- P7: Phase Closing

Features demonstrated:
- Multi-level workflow (Milestones + Phases)
- USER-APPROVE items
- Rulesets for condition reuse
- File and command validators
- Sub-agent review integration

**Try it:**
```bash
cd examples/full-project
flow status
flow tutorial --list
```

---

### 3. Custom Plugins (`custom-plugins/`)

**Best for:** Advanced users, specialized requirements

Demonstrates how to create and use custom validators:
- Git branch validator
- Code coverage validator
- API health checker

Features demonstrated:
- Creating custom BaseValidator subclasses
- Registering plugins in workflow.yaml
- Using plugin conditions in transitions
- Combining multiple validators

**Try it:**
```bash
cd examples/custom-plugins
flow status
# Review validators/custom.py for implementation details
```

---

## How to Use Examples

### Method 1: Copy to Your Project

```bash
# Copy desired example
cp -r examples/simple/* /path/to/your/project/

# Navigate and use
cd /path/to/your/project
flow status
```

### Method 2: Run In-Place

```bash
# Navigate to example directory
cd examples/full-project

# The workflow.yaml is auto-detected
flow status
```

### Method 3: Reference for Learning

Read the workflow.yaml files to understand patterns:
```bash
cat examples/simple/workflow.yaml
cat examples/full-project/workflow.yaml
```

---

## Customization Guide

### Starting from Simple

1. Copy `simple/` to your project
2. Modify stage names to match your process
3. Adjust checklists for your needs
4. Add more stages as needed

### Starting from Full-Project

1. Copy `full-project/` to your project
2. Rename milestone-specific items
3. Adjust phase checklists
4. Enable/disable plugins as needed

### Creating Custom Workflows

1. Start with the structure that matches your needs
2. Add stages in logical order
3. Define meaningful checklists (3-7 items per stage)
4. Set up transitions with appropriate conditions
5. Add plugins for automated validation

---

## Tips for Effective Workflows

### Checklist Design

**Good checklists:**
```yaml
checklist:
  - "Write unit tests for new functions"
  - "Run linter and fix all errors"
  - "Update API documentation"
```

**Avoid vague items:**
```yaml
# Bad - too vague
checklist:
  - "Do testing"
  - "Fix stuff"
  - "Make it work"
```

### Transition Conditions

**Use validators for automation:**
```yaml
transitions:
  - target: "DEPLOY"
    conditions:
      - rule: shell
        args:
          cmd: "pytest"
        fail_message: "Tests must pass before deployment"
```

### USER-APPROVE Strategic Placement

Put USER-APPROVE at critical decision points:
```yaml
checklist:
  - "Review security implications"
  - "Check performance impact"
  - "[USER-APPROVE] Approve for production deployment"
```

---

## Troubleshooting Examples

### "workflow.yaml not found"

Ensure you're in the example directory:
```bash
pwd  # Should show examples/simple or similar
ls   # Should show workflow.yaml
```

### "State file not found"

Initialize with first command:
```bash
flow status  # Creates .workflow/state.json
```

### Plugin import errors

For custom-plugins example, ensure Python path:
```bash
cd examples/custom-plugins
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
flow status
```

---

## Contributing Examples

Have a useful workflow pattern? Contribute it!

1. Create a new directory under `examples/`
2. Include:
   - `workflow.yaml` - The workflow configuration
   - `.workflow/state.json` - Initial state
   - `README.md` - Description and usage
3. Document what problem it solves
4. Submit a pull request

---

## See Also

- Main [README.md](../README.md) for full documentation
- [Tutorial](../workflow/tutorial/) for learning materials
- [PROJECT_MANAGEMENT_GUIDE.md](../.workflow/docs/PROJECT_MANAGEMENT_GUIDE.md) for the full methodology
