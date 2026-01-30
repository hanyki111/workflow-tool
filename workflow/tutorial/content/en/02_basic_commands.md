# Basic Commands

Learn the essential commands for managing your workflow.

## Status Command

Check your current position in the workflow:

```bash
flow status
```

Output example:
```
=== Current Stage: M0 (Tech Debt Review) ===
Active Module: core-engine

Checklist:
[ ] 1. Review discovered debts with user
[x] 2. Run search for Technical Debt
[ ] 3. Decide which debts to address

Progress: 1/3 items completed
```

### One-line Status

```bash
flow status --oneline
# Output: M0 (Tech Debt Review) - 1/3
```

## Check Command

Mark checklist items as completed:

```bash
# Check single item (1-based index)
flow check 1

# Check multiple items
flow check 1 2 3

# Add evidence/justification
flow check 1 --evidence "Reviewed all modules, no critical debt found"

# Pass arguments to action commands
flow check 5 --args "feat: add user authentication"
```

### Active Workflow (Action Execution)

If a checklist item has an `action` defined in workflow.yaml, it executes automatically:

```bash
$ flow check 1
✅ Action executed: pytest -v
   Output: 15 passed in 2.34s
Checked: Run tests
```

If the action fails, the item is NOT marked as checked:

```bash
$ flow check 1
❌ Action failed for item 1: Command failed with exit code 1
```

**Built-in variables:** Use `${python}` for the current Python interpreter (venv-aware), `${cwd}` for the working directory. Actions inherit the full shell environment.

## Next Command

Transition to the next stage:

```bash
# Auto-detect next stage
flow next

# Specify target stage
flow next M1

# Force transition (skips rules)
flow next --force --reason "Emergency hotfix needed"
```

### Transition Errors

If conditions aren't met:
```
Cannot transition: All checklist items must be completed
Remaining items: 2, 3
```

## Set Command

Manually set stage or module:

```bash
# Set stage
flow set M2

# Set stage and module
flow set P3 --module inventory-system
```

## Command Combinations

Typical workflow:
```bash
# 1. Check status
flow status

# 2. Complete work and check items
flow check 1
flow check 2 3

# 3. Move to next stage
flow next
```

## Tips

- Always run `flow status` before starting work
- Check items as you complete them, not all at once
- Use `--evidence` for important decisions
- Don't use `--force` unless absolutely necessary

Next: Learn about security and secrets!
