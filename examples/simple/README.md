# Simple Workflow Example

A minimal 3-stage workflow for small projects or learning purposes.

## Overview

```
START → DEVELOP → DONE
```

This workflow is intentionally simple:
- **START**: Project initialization
- **DEVELOP**: Implementation work
- **DONE**: Completion and wrap-up

## Files

- `workflow.yaml` - Workflow configuration
- `.workflow/state.json` - Current state

## Usage

```bash
# Navigate to this directory
cd examples/simple

# Check current status
flow status

# Output:
# Current Stage: START (Project Start)
# ========================================
# 1. [ ] Define project scope
# 2. [ ] Set up development environment
# 3. [ ] Create initial file structure

# Complete items
flow check 1 2 3

# Move to next stage
flow next

# Continue through DEVELOP stage
flow status
flow check 1 2 3
flow next

# Complete the workflow
flow status
flow check 1 2
flow next
```

## Customization Ideas

### Add a Review Stage

```yaml
stages:
  # ... existing stages ...

  REVIEW:
    id: "REVIEW"
    label: "Code Review"
    checklist:
      - "Self-review completed"
      - "Peer review requested"
      - "[USER-APPROVE] Approved by reviewer"
    transitions:
      - target: "DONE"
```

### Add Automated Tests

```yaml
plugins:
  shell: "workflow.plugins.shell.CommandValidator"

stages:
  DEVELOP:
    transitions:
      - target: "DONE"
        conditions:
          - rule: all_checked
          - rule: shell
            args:
              cmd: "pytest tests/"
            fail_message: "Tests must pass"
```

### Add File Checks

```yaml
plugins:
  fs: "workflow.plugins.fs.FileExistsValidator"

stages:
  DONE:
    checklist:
      - "Update README"
      - "Add changelog entry"
    transitions:
      - target: "START"  # Loop back for next iteration
        conditions:
          - rule: fs
            args:
              path: "README.md"
              not_empty: true
```

## When to Use This

- Learning the workflow tool
- Small scripts or utilities
- Quick prototypes
- Single-developer projects

For larger projects, see `examples/full-project/`.
