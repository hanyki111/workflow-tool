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

## Guide File Integration

Sync checklists from your project documentation (any markdown file):

```yaml
# workflow.yaml
guide_file: "docs/WORKFLOW_GUIDE.md"

stages:
  REVIEW:
    label: "Code Review"  # Matches header in guide file
    checklist: []         # Empty - synced from guide file
```

**Guide file (`docs/WORKFLOW_GUIDE.md`):**
```markdown
## Code Review

- [ ] All tests pass
- [ ] Code follows style guide
- [ ] [USER-APPROVE] Security review
```

The engine finds the header matching the stage label and extracts checkboxes below it.

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

### AI CLI Hook Integration (Automation)

Fully automate agent review registration using CLI hooks.
Both **Claude Code** and **Gemini CLI** are supported.

**Claude Code setup:**
```bash
mkdir -p .claude/hooks
cp examples/hooks/auto-review.sh .claude/hooks/
chmod +x .claude/hooks/auto-review.sh
```

`.claude/settings.json`:
```json
{
  "hooks": {
    "PostToolUse": [{ "matcher": "Task", "hooks": [{ "type": "command", "command": ".claude/hooks/auto-review.sh" }] }]
  }
}
```

**Gemini CLI setup:**
```bash
mkdir -p .gemini/hooks
cp examples/hooks/auto-review.sh .gemini/hooks/
chmod +x .gemini/hooks/auto-review.sh
```

`settings.json`:
```json
{
  "hooks": {
    "AfterTool": [{ "matcher": "spawn_agent|delegate", "hooks": [{ "type": "command", "command": "$GEMINI_PROJECT_DIR/.gemini/hooks/auto-review.sh" }] }]
  }
}
```

**How it works:**
1. AI calls agent delegation tool
2. Hook intercepts completion (PostToolUse/AfterTool)
3. Hook extracts agent name, calls `flow review`
4. `[AGENT:name]` items now pass `flow check`

### Session Start Hook (Auto-load Workflow Status)

Automatically show workflow status when AI starts a session.

**Claude Code** (`.claude/settings.json`):
```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [{ "type": "command", "command": "flow status 2>/dev/null || echo 'No workflow initialized'" }]
      },
      {
        "matcher": "resume",
        "hooks": [{ "type": "command", "command": "flow status --oneline 2>/dev/null || true" }]
      }
    ]
  }
}
```

**Gemini CLI** (`settings.json`):
```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [{ "type": "command", "command": "flow status 2>/dev/null || echo 'No workflow initialized'" }]
      },
      {
        "matcher": "resume",
        "hooks": [{ "type": "command", "command": "flow status --oneline 2>/dev/null || true" }]
      }
    ]
  }
}
```

**Matchers:**
| Matcher | Trigger |
|---------|---------|
| `startup` | New session |
| `resume` | Resume existing session |
| `clear` | After `/clear` command |
| `compact` | After context compaction (Claude Code only) |

**Result:** When AI starts, it automatically sees the current workflow state in its context.

### User Prompt Hook (Real-time Status on Every Input)

Show workflow status every time user submits a prompt (not just session start).

**Claude Code** - `UserPromptSubmit` (`.claude/settings.json`):
```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [{ "type": "command", "command": "flow status --oneline 2>/dev/null || true" }]
      }
    ]
  }
}
```

**Gemini CLI** - `BeforeModel` (`settings.json`):
```json
{
  "hooks": {
    "BeforeModel": [
      {
        "hooks": [{ "type": "command", "command": "flow status --oneline 2>/dev/null || true" }]
      }
    ]
  }
}
```

**Comparison:**
| Hook | Trigger | Use Case |
|------|---------|----------|
| `SessionStart` | Once at session start/resume | Initial context loading |
| `UserPromptSubmit` / `BeforeModel` | Every user prompt | Real-time status tracking |

**Recommended combined setup:**
```json
{
  "hooks": {
    "SessionStart": [
      { "matcher": "startup", "hooks": [{ "type": "command", "command": "flow status 2>/dev/null || true" }] }
    ],
    "UserPromptSubmit": [
      { "hooks": [{ "type": "command", "command": "flow status --oneline 2>/dev/null || true" }] }
    ]
  }
}
```

- Session start: Full status display
- Each prompt: One-line status (minimal overhead)

## Automated Checking with Shell Wrappers

Automate checklist updates when specific CLI commands succeed using tags and shell wrappers.

### Step 1: Add Tags to Checklist Items

```yaml
# workflow.yaml
stages:
  P3:
    checklist:
      - "[CMD:pytest] Run tests"
      - "[CMD:memory-write] Save documentation with memory tool"
      - "[CMD:lint] Run linter"
```

### Step 2: Create Shell Wrappers

```bash
# .bashrc or project/.envrc

# pytest wrapper
pytest() {
    command pytest "$@"
    [ $? -eq 0 ] && flow check --tag "CMD:pytest" 2>/dev/null
}

# memory_tool wrapper (subcommand-aware)
memory_tool() {
    command memory_tool "$@"
    [ $? -eq 0 ] && case "$1" in
        write|save) flow check --tag "CMD:memory-write" ;;
    esac
}

# lint wrapper
lint() {
    command ruff check . "$@"
    [ $? -eq 0 ] && flow check --tag "CMD:lint" 2>/dev/null
}
```

### Step 3: Use Normally

```bash
# Run pytest normally - checklist auto-updates on success
pytest tests/
# ✅ Auto-checked: [CMD:pytest] Run tests

# Memory tool - only 'write' subcommand triggers check
memory_tool write docs/spec.md
# ✅ Auto-checked: [CMD:memory-write] Save documentation with memory tool

memory_tool read docs/spec.md
# (no checklist update - read is not mapped)
```

### Tag Matching

The `--tag` option finds and checks **all unchecked items** containing the tag:

```bash
flow check --tag "CMD:pytest"
# Finds items containing "[CMD:pytest]" and checks them
```

**Benefits:**
- Works for both AI and human-executed commands
- Subcommand-aware (only specific actions trigger checks)
- No need to know item index numbers
- Explicit tags prevent accidental matches

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

## Conditional Rules (when clause)

Skip conditions based on context using the `when` clause:

```yaml
stages:
  P3:
    transitions:
      - target: P4
        conditions:
          # Only check implementation directory for code modules
          - rule: fs
            when: '${active_module} not in ["roadmap", "docs", "planning"]'
            args:
              path: "src/${active_module}/"
            fail_message: "Implementation directory not found"

          # Only run tests for code modules
          - rule: shell
            when: '${active_module} not in ["roadmap", "docs"]'
            args:
              cmd: "pytest tests/${active_module}/"
```

### Supported Operators

| Operator | Example | Description |
|----------|---------|-------------|
| `==` | `${var} == "value"` | Equality |
| `!=` | `${var} != "value"` | Inequality |
| `in` | `${var} in ["a", "b"]` | List membership |
| `not in` | `${var} not in ["a", "b"]` | List non-membership |

### Use Cases

**Meta modules (roadmap, docs):** Skip code-related validations
```yaml
- rule: shell
  when: '${active_module} != "roadmap"'
  args:
    cmd: "pytest"
```

**Stage-specific conditions:**
```yaml
- rule: fs
  when: '${current_stage} == "P6"'
  args:
    path: "CHANGELOG.md"
```

When a `when` condition evaluates to false, the rule is marked as `SKIPPED` in the audit log.

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

## Ralph Loop Mode

Automatically retry via Task subagent until success when action fails.

### Basic Configuration (exit code based)

```yaml
# workflow.yaml
stages:
  IMPL:
    checklist:
      - text: "Pass tests"
        action: "pytest"
        ralph:
          enabled: true       # Enable Ralph mode
          max_retries: 5      # Maximum retry attempts
          hint: "Analyze failing tests and fix the code"
```

### Output Pattern Matching (success_contains / fail_contains)

Judge success/failure by output content, like agent review results:

```yaml
checklist:
  - text: "Pass code review"
    action: "cat .workflow/code_review.md"
    ralph:
      enabled: true
      max_retries: 5
      success_contains:           # Success if any of these found
        - "**PASS**"
        - "**CONDITIONAL PASS**"
      fail_contains:              # Fail if any of these found (priority)
        - "**FAIL**"
      hint: "Run code-reviewer agent and fix FAIL issues"
```

**Judgment Logic:**
1. Check `fail_contains` first (higher priority)
2. Check `success_contains`
3. Fall back to exit code if no patterns defined

### How It Works

```
flow check 1
    │
    ├─ Success → ✅ Item checked
    │
    └─ Failure (ralph enabled)
           │
           ▼
    🔄 [RALPH MODE] Action failed (attempt 1/5)

    Goal: Make `pytest` succeed
    Error: FAILED test_auth.py::test_login

    📋 Instructions for Task subagent:
    1. Analyze error and fix code
    2. Run flow check 1 again
    3. Repeat until success
           │
           ▼
    Claude runs Task subagent
           │
           ▼
    Subagent: fix → flow check 1 → (repeat)
```

### Key Concepts

Ralph Loop is an autonomous AI agent execution technique proposed by Geoffrey Huntley:

| Feature | Description |
|---------|-------------|
| **File-based state** | Progress stored in `.workflow/ralph_state.json` |
| **Fresh context** | Subagent starts with new context each time |
| **Auto-reset** | State cleared on success or stage change |

### Force Check (Bypass Ralph)

```bash
# To force check after max retries exceeded:
flow check 1 --skip-action
```

## Cross-Platform Support

Two features for Windows/Unix compatibility without shell dependency issues.

### file_check: Shell-Free File Checking

Check file contents using pure Python - works identically on all platforms:

```yaml
checklist:
  - text: "Review passed"
    file_check:
      path: ".workflow/reviews/critic.md"
      success_contains: ["APPROVED", "CONDITIONAL PASS"]
      fail_contains: ["FAIL"]
      fail_if_missing: true
    ralph:
      enabled: true
      max_retries: 3
```

**Options:**
| Option | Description |
|--------|-------------|
| `path` | File path (supports `${variables}`) |
| `success_contains` | Pass if any pattern found |
| `fail_contains` | Fail if any pattern found (priority) |
| `fail_if_missing` | Fail if file doesn't exist |
| `encoding` | File encoding (default: utf-8) |

**Use instead of:**
```yaml
# Don't do this (shell-dependent):
action: "cat .workflow/reviews/critic.md | grep APPROVED"

# Do this (cross-platform):
file_check:
  path: ".workflow/reviews/critic.md"
  success_contains: ["APPROVED"]
```

**Note:** `file_check` and `action` are mutually exclusive.

### Platform-Specific Actions

When you need different commands per platform:

```yaml
checklist:
  - text: "Build project"
    action:
      unix: "make build"
      windows: "msbuild project.sln"
      all: "python build.py"  # Optional: overrides both
```

**Priority:** `all` > platform-specific

**Platform detection:** `sys.platform == 'win32'` for Windows

**Example - Conditional build:**
```yaml
checklist:
  - text: "Run linter"
    action:
      unix: "./scripts/lint.sh"
      windows: "powershell scripts/lint.ps1"

  - text: "Compile"
    action:
      all: "python -m build"  # Same for all platforms
```

### Ralph Integration

Both features work with Ralph Loop:

```yaml
- text: "Verify deployment"
  file_check:
    path: ".workflow/deploy_status.txt"
    success_contains: ["DEPLOYED"]
    fail_if_missing: true
  ralph:
    enabled: true
    max_retries: 5
    hint: "Run deployment script and check status"
```

On failure, Ralph prompt shows file content for debugging.

Next: Best practices and tips!
