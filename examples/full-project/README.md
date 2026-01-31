# Full Project Workflow Example

A complete dual-track workflow demonstrating the M0-M4 + P1-P7 methodology.

## Overview

This workflow implements the two-track system:

### Milestone Track (M0-M4)
High-level project phases that span the entire milestone:

```
M0 (Tech Debt) → M1 (Planning) → M2 (Discussion) → M3 (Branch)
                                                        ↓
                    ┌──────────────────────────────────┘
                    ↓
              [Phase Loop]
                    ↓
              M4 (Closing)
```

### Phase Track (P1-P7)
Detailed implementation steps, repeated for each phase:

```
P1 (Planning) → P2 (Discussion) → P3 (Spec) → P4 (Implementation)
                                                      ↓
P7 (Closing) ← P6 (Review) ← P5 (Testing) ←──────────┘
```

## Stage Details

### Milestone Stages

| Stage | Purpose | Key Activities |
|-------|---------|----------------|
| M0 | Tech Debt Review | Assess existing debt, prioritize fixes |
| M1 | Milestone Planning | Create PRD, define scope, estimate work |
| M2 | Milestone Discussion | Architecture review, get user approval |
| M3 | Branch Creation | Git setup, create feature branch |
| M4 | Milestone Closing | Merge, document, deploy |

### Phase Stages

| Stage | Purpose | Key Activities |
|-------|---------|----------------|
| P1 | Phase Planning | Review PRD, define deliverables |
| P2 | Phase Discussion | Technical design, user approval |
| P3 | Spec | Write technical specification |
| P4 | Implementation | Code implementation |
| P5 | Testing | Unit tests, integration tests |
| P6 | Self-Review | Code quality, SOLID principles |
| P7 | Phase Closing | Documentation sync, commit |

## Features Demonstrated

### 1. USER-APPROVE Items

Critical decisions require human verification:

```yaml
checklist:
  - "[USER-APPROVE] Approve milestone plan"
```

Usage:
```bash
flow secret-generate              # First time setup
flow check 3 --token "secret"     # Check with verification
```

### 2. Rulesets

Reusable condition groups:

```yaml
rulesets:
  ready_for_next:
    - rule: all_checked
    - rule: user_approved
```

### 3. File Validators

Ensure required files exist:

```yaml
conditions:
  - rule: fs
    args:
      path: "docs/spec.md"
      not_empty: true
```

### 4. Command Validators

Automate test verification:

```yaml
conditions:
  - rule: shell
    args:
      cmd: "pytest tests/"
      expect_code: 0
```

## Usage

```bash
# Navigate to this directory
cd examples/full-project

# Check current status (starts at M0)
flow status

# Work through tech debt review
flow check 1
flow check 2
flow check 3 --token "your-secret"  # USER-APPROVE
flow next

# Continue through milestone stages
flow status  # Now at M1
# ... follow the checklist
```

## Typical Workflow Session

### Session 1: Start New Milestone

```bash
# Check status
flow status
# Output: M0 (Tech Debt Review)

# Complete tech debt review
flow check 1 --evidence "Reviewed all modules, 3 debt items found"
flow check 2 --evidence "Prioritized: fix auth bug, refactor DB layer"
flow check 3 --token "secret" --evidence "Approved debt plan"
flow next

# Create milestone plan
flow status  # M1 (Milestone Planning)
flow check 1 --evidence "Created m24-user-auth.md"
flow check 2
flow check 3
flow next
```

### Session 2: Architecture Review

```bash
flow status  # M2 (Milestone Discussion)
flow check 1 --evidence "Presented OAuth2 flow diagram"
flow check 2 --evidence "Applied Pre-mortem and Devil's Advocate"
flow check 3
flow check 4 --token "secret" --evidence "User approved architecture"
flow next
```

### Session 3: Implementation Phase

```bash
flow status  # P1 (Phase Planning)
# ... work through P1-P7 for each phase
```

## Customization

### Adjust for Your Team

1. Modify stage labels to match your terminology
2. Add/remove checklist items as needed
3. Enable/disable plugins based on your tooling

### Simplify for Smaller Projects

Remove some Phase stages if they're overkill:
- Keep: P1, P4, P5, P7
- Optional: P2, P3, P6

### Add Project-Specific Validators

```yaml
plugins:
  coverage: "myproject.validators.CoverageValidator"

stages:
  P5:
    transitions:
      - target: "P6"
        conditions:
          - rule: coverage
            args:
              minimum: 80
```

## Files

- `workflow.yaml` - Complete workflow configuration
- `.workflow/state.json` - Current state
- `.workflow/secret` - Secret hash (create with `flow secret-generate`)

## Tips

1. **Don't skip M0**: Tech debt review prevents accumulation
2. **Use evidence**: `--evidence` creates audit trail
3. **USER-APPROVE strategically**: Only for critical decisions
4. **Complete phases fully**: Don't rush P6 (Review) and P7 (Closing)

## Related

- [Main README](../../README.md) - Full documentation
- [Tutorial](../../workflow/tutorial/) - Learning materials
