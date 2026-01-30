# Best Practices

Tips and patterns for effective workflow management.

## Workflow Design

### 1. Keep Stages Focused
Each stage should have a clear, single purpose:
- Good: "Write unit tests"
- Bad: "Write tests, fix bugs, and update docs"

### 2. Checklist Granularity
- 3-7 items per stage is ideal
- Too few = not enough guidance
- Too many = overwhelming

### 3. Meaningful Conditions
Don't just check "all_checked". Add real validation:
```yaml
conditions:
  - use_ruleset: all_checked
  - rule: shell
    args:
      cmd: "pytest"  # Actually run tests
```

## Daily Workflow

### Starting Work
```bash
# Always start with status
flow status

# Read the checklist
# Understand what needs to be done
```

### During Work
```bash
# Check items as you complete them
flow check 1

# Not all at once at the end
# This maintains accurate progress tracking
```

### Ending Work
```bash
# Check remaining items
flow status

# If incomplete, document progress
flow check 2 --evidence "Partially complete, tests written but need review"
```

## AI Collaboration

### Context Awareness
Instruct your AI assistant to:
1. Run `flow status` at the start of each session
2. Follow the checklist items in order
3. Check items after completing each task

### Example Instruction
```
Before starting any task, run `flow status` and follow
the checklist. Check off items as you complete them
using `flow check N`. Don't proceed to the next stage
until all items are verified.
```

## Troubleshooting

### "Cannot transition" Error
```bash
# Check what's missing
flow status

# Complete remaining items
flow check 3 4

# Try again
flow next
```

### State Corruption
```bash
# Reset to a known state
flow set M0

# Or manually edit .workflow/state.json
```

### Plugin Load Errors
```bash
# Check plugin path in workflow.yaml
# Ensure module is importable:
python -c "from workflow.plugins.fs import FileExistsValidator"
```

## Anti-Patterns

### Don't:
- ❌ Use `--force` regularly
- ❌ Check all items without doing the work
- ❌ Skip USER-APPROVE items
- ❌ Commit `.workflow/secret` to git

### Do:
- ✅ Check items as you complete them
- ✅ Add evidence for important decisions
- ✅ Run `flow status` frequently
- ✅ Follow stage order

## Team Usage

### Shared Configuration
- `workflow.yaml`: Commit to git
- `.workflow/state.json`: Per-developer (gitignore)
- `.workflow/secret`: Per-developer (gitignore)

### Consistent Process
- All team members use the same workflow definition
- Individual state allows parallel work
- Review stages ensure quality gates

---

Congratulations! You've completed the workflow-tool tutorial.

For more information:
- Documentation: `.memory/docs/`
- Configuration: `workflow.yaml`
- Issues: https://github.com/workflow-tool/workflow-tool/issues
