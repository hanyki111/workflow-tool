# Advanced Features

This section covers advanced workflow configuration and usage.

## Custom Validators (Plugins)

### Built-in Plugins

**FileExistsValidator**: Check if files exist
```yaml
plugins:
  fs: "workflow.plugins.fs.FileExistsValidator"

stages:
  P4:
    transitions:
      - target: P5
        conditions:
          - rule: fs
            args:
              path: "src/main.py"
              not_empty: true
```

**CommandValidator**: Run shell commands
```yaml
plugins:
  shell: "workflow.plugins.shell.CommandValidator"

stages:
  P5:
    transitions:
      - target: P6
        conditions:
          - rule: shell
            args:
              cmd: "pytest tests/ -v"
              expect_code: 0
```

### Creating Custom Plugins

1. Create plugin file:
```python
# workflow/plugins/my_validator.py
from ..core.validator import BaseValidator

class MyValidator(BaseValidator):
    def validate(self, args, context):
        # Your validation logic
        return True  # or False
```

2. Register in workflow.yaml:
```yaml
plugins:
  my_check: "workflow.plugins.my_validator.MyValidator"
```

## Rulesets

Group conditions for reuse:

```yaml
rulesets:
  ready_for_deploy:
    - rule: all_checked
    - rule: shell
      args:
        cmd: "pytest"
    - rule: fs
      args:
        path: "CHANGELOG.md"

stages:
  P6:
    transitions:
      - target: P7
        conditions:
          - use_ruleset: ready_for_deploy
```

## Sub-Agent Reviews

Record AI sub-agent reviews:

```bash
flow review --agent "code-reviewer" --summary "All SOLID principles followed, no issues found"
```

This creates an audit record that can be verified later.

### Streamlined Check with --agent

Check `[AGENT:name]` items with inline registration:

```bash
# Instead of two commands:
flow review --agent plan-critic --summary "..."
flow check 1

# Use one command:
flow check 1 --agent plan-critic
```

### Claude Code Hook Integration (Automation)

Fully automate agent review registration using Claude Code hooks.

**1. Setup hook script:**
```bash
mkdir -p .claude/hooks
cp examples/hooks/auto-review.sh .claude/hooks/
chmod +x .claude/hooks/auto-review.sh
```

**2. Configure `.claude/settings.json`:**
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Task",
        "hooks": [{
          "type": "command",
          "command": ".claude/hooks/auto-review.sh"
        }]
      }
    ]
  }
}
```

**How it works:**
1. AI calls Task tool with `subagent_type: "code-reviewer"`
2. PostToolUse hook intercepts completion
3. Hook extracts agent name, calls `flow review`
4. `[AGENT:code-reviewer]` items now pass `flow check`

## Variables

Define project-wide variables:

```yaml
variables:
  project_name: "my-app"
  version: "2.0.0"
  test_command: "pytest -v"
```

Use in conditions:
```yaml
conditions:
  - rule: shell
    args:
      cmd: "${test_command}"
```

## Stage Hooks (on_enter)

Execute actions when entering a stage:

```yaml
stages:
  P4:
    on_enter:
      - action: "notify"
        args:
          message: "Starting implementation"
      - action: "shell"
        args:
          cmd: "git status"
```

## Conditional Transitions

Multiple targets based on conditions:

```yaml
stages:
  P7:
    transitions:
      # If all phases complete, go to M4
      - target: "M4"
        conditions:
          - rule: all_phases_complete
      # Otherwise, go to next phase
      - target: "P1"
        conditions:
          - use_ruleset: all_checked
```

Next: Best practices and tips!
