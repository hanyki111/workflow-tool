"""Project initialization for workflow-tool."""
import os
import json
import shutil
from pathlib import Path
from typing import Optional

from .i18n import t


# Template: Simple workflow
SIMPLE_WORKFLOW = '''version: "2.0"

variables:
  project_name: "{project_name}"

plugins:
  file_exists: "workflow.plugins.fs.FileExistsValidator"
  cmd_success: "workflow.plugins.shell.CommandValidator"

rulesets:
  all_checked:
    - rule: all_checked
      fail_message: "All checklist items must be completed"

stages:
  START:
    id: "START"
    label: "Project Start"
    checklist:
      - "Define project scope and goals"
      - "Set up development environment"
      - "Create initial structure"
    transitions:
      - target: "DEVELOP"
        conditions:
          - use_ruleset: all_checked

  DEVELOP:
    id: "DEVELOP"
    label: "Development"
    checklist:
      - "Implement core functionality"
      - "Write tests"
      - "Run tests and verify"
    transitions:
      - target: "REVIEW"
        conditions:
          - use_ruleset: all_checked

  REVIEW:
    id: "REVIEW"
    label: "Review"
    checklist:
      - "Self-review code quality"
      - "Update documentation"
      - "[USER-APPROVE] Final approval"
    transitions:
      - target: "DONE"
        conditions:
          - use_ruleset: all_checked

  DONE:
    id: "DONE"
    label: "Complete"
    checklist:
      - "Commit changes"
      - "Update changelog"
    transitions:
      - target: "START"
        conditions:
          - use_ruleset: all_checked
'''

# Template: Full M0-M4, P1-P7 workflow
FULL_WORKFLOW = '''version: "2.0"

variables:
  project_name: "{project_name}"
  active_module: "core"

plugins:
  file_exists: "workflow.plugins.fs.FileExistsValidator"
  cmd_success: "workflow.plugins.shell.CommandValidator"

rulesets:
  all_checked:
    - rule: all_checked
      fail_message: "All checklist items must be completed"

  user_approved:
    - rule: user_approved
      fail_message: "USER-APPROVE items require verification token"

# =============================================================================
# MILESTONE STAGES (M0-M4)
# =============================================================================
stages:
  M0:
    id: "M0"
    label: "Tech Debt Review"
    checklist:
      - "Search for existing technical debt"
      - "Review and prioritize debt items"
      - "[USER-APPROVE] Approve debt plan"
    transitions:
      - target: "M1"
        conditions:
          - use_ruleset: all_checked

  M1:
    id: "M1"
    label: "Milestone Planning"
    checklist:
      - "Create milestone PRD document"
      - "Define objectives and success criteria"
      - "Identify phases and goals"
      - "Estimate scope and dependencies"
    transitions:
      - target: "M2"
        conditions:
          - use_ruleset: all_checked

  M2:
    id: "M2"
    label: "Milestone Discussion"
    checklist:
      - "Present architecture and strategy"
      - "Apply thinking tools (Pre-mortem, etc.)"
      - "Discuss risks and trade-offs"
      - "[USER-APPROVE] Approve milestone plan"
    transitions:
      - target: "M3"
        conditions:
          - use_ruleset: all_checked

  M3:
    id: "M3"
    label: "Branch Creation"
    checklist:
      - "Update main branch (git pull)"
      - "Create feature branch"
      - "Verify branch creation"
    transitions:
      - target: "P1"
        conditions:
          - use_ruleset: all_checked

  M4:
    id: "M4"
    label: "Milestone Closing"
    checklist:
      - "Run full test suite"
      - "Merge to main branch"
      - "Push to remote"
      - "Update documentation"
    transitions:
      - target: "M0"
        conditions:
          - use_ruleset: all_checked

# =============================================================================
# PHASE STAGES (P1-P7)
# =============================================================================
  P1:
    id: "P1"
    label: "Phase Planning"
    checklist:
      - "Review PRD for phase objectives"
      - "Define specific deliverables"
      - "Update PRD if needed"
    transitions:
      - target: "P2"
        conditions:
          - use_ruleset: all_checked

  P2:
    id: "P2"
    label: "Phase Discussion"
    checklist:
      - "Propose detailed design"
      - "Discuss technical approach"
      - "Identify risks or blockers"
      - "[USER-APPROVE] Approve before spec"
    transitions:
      - target: "P3"
        conditions:
          - use_ruleset: all_checked

  P3:
    id: "P3"
    label: "Specification"
    checklist:
      - "Create/update module structure"
      - "Write technical spec (spec.md)"
      - "Update related files section"
      - "Check if architecture update needed"
    transitions:
      - target: "P4"
        conditions:
          - use_ruleset: all_checked

  P4:
    id: "P4"
    label: "Implementation"
    checklist:
      - "Create files based on spec"
      - "Implement logic following spec"
      - "Verify imports and dependencies"
    transitions:
      - target: "P5"
        conditions:
          - use_ruleset: all_checked

  P5:
    id: "P5"
    label: "Testing"
    checklist:
      - "Write unit tests"
      - "Write integration tests"
      - "Run all tests"
    transitions:
      - target: "P6"
        conditions:
          - use_ruleset: all_checked

  P6:
    id: "P6"
    label: "Self-Review"
    checklist:
      - "Check spec alignment"
      - "Review error handling"
      - "Verify code quality"
      - "[USER-APPROVE] Approve for closing"
    transitions:
      - target: "P7"
        conditions:
          - use_ruleset: all_checked

  P7:
    id: "P7"
    label: "Phase Closing"
    checklist:
      - "Update spec if deviated"
      - "Record tech debt if any"
      - "Git commit with message"
      - "Update phase status"
    transitions:
      - target: "P1"
        conditions:
          - use_ruleset: all_checked
      - target: "M4"
        conditions:
          - use_ruleset: all_checked
'''

# Template: Initial state
INITIAL_STATE = '''{{
  "current_milestone": "",
  "current_phase": "",
  "current_stage": "{initial_stage}",
  "active_module": "",
  "checklist": []
}}
'''

# Template: PROJECT_MANAGEMENT_GUIDE.md (minimal)
GUIDE_TEMPLATE = '''# Project Management Guide

This project uses the AI Workflow Engine for structured development.

---

## Workflow Overview

Run `flow status` to see current stage and checklist.

---

{stage_docs}
'''

# Template: Workflow instructions for AI (to be added to existing CLAUDE.md)
WORKFLOW_INSTRUCTIONS_TEMPLATE = '''
## Workflow Protocol (MANDATORY)

> **This project uses `workflow-tool` for structured development.**

### Setup (Add to top of CLAUDE.md)

```markdown
@import .memory/ACTIVE_STATUS.md
```

### Every Turn

1. **Run** `flow status` to check current stage and checklist
2. **State** current stage: `**[Stage XX]** Stage Name`
3. **Follow** checklist items in order
4. **Check** items as completed: `flow check N --evidence "description"`
5. **Advance** when ready: `flow next`

### Stage Declaration Format

```
**[Stage M2]** Milestone Discussion
**[Stage P4]** Implementation (Phase 1.2)
```

### Commands Reference

| Command | Usage |
|---------|-------|
| `flow status` | Check current state |
| `flow check N` | Mark item N as done |
| `flow check N --evidence "..."` | Mark with evidence |
| `flow check N --token "..."` | USER-APPROVE items |
| `flow next` | Move to next stage |
| `flow set XX` | Jump to stage XX |

### USER-APPROVE Items

When encountering `[USER-APPROVE]` items, ask the user to run:

```bash
flow check N --token "their-secret"
```

### Prohibited Actions

- Do NOT skip checklist items
- Do NOT use `--force` without explicit permission
- Do NOT ignore USER-APPROVE requirements
'''

# Minimal snippet to add to existing CLAUDE.md
CLAUDE_MD_SNIPPET = '''
# ============================================================
# Workflow Tool Integration
# ============================================================
# Add this line at the TOP of your CLAUDE.md:
#   @import .memory/ACTIVE_STATUS.md
#
# Add the section below to your CLAUDE.md:
# ============================================================

## Workflow Protocol

> This project uses `workflow-tool`. Run `flow status` at the start of every turn.

**Quick Reference:**
- `flow status` - Check current stage and checklist
- `flow check N` - Mark item N as done
- `flow check N --evidence "..."` - Mark with justification
- `flow check N --token "..."` - For [USER-APPROVE] items
- `flow next` - Move to next stage

**Rules:**
1. Always run `flow status` first
2. State current stage: `**[Stage XX]** Name`
3. Complete checklist items in order
4. Never skip [USER-APPROVE] items
'''


def generate_stage_docs(template: str) -> str:
    """Generate stage documentation from template."""
    if template == "simple":
        return '''## Project Start

**Checklist:**

- [ ] Define project scope and goals
- [ ] Set up development environment
- [ ] Create initial structure

---

## Development

**Checklist:**

- [ ] Implement core functionality
- [ ] Write tests
- [ ] Run tests and verify

---

## Review

**Checklist:**

- [ ] Self-review code quality
- [ ] Update documentation
- [ ] [USER-APPROVE] Final approval

---

## Complete

**Checklist:**

- [ ] Commit changes
- [ ] Update changelog
'''
    else:
        return '''## Tech Debt Review

**Checklist:**

- [ ] Search for existing technical debt
- [ ] Review and prioritize debt items
- [ ] [USER-APPROVE] Approve debt plan

---

## Milestone Planning

**Checklist:**

- [ ] Create milestone PRD document
- [ ] Define objectives and success criteria
- [ ] Identify phases and goals
- [ ] Estimate scope and dependencies

---

## Milestone Discussion

**Checklist:**

- [ ] Present architecture and strategy
- [ ] Apply thinking tools (Pre-mortem, etc.)
- [ ] Discuss risks and trade-offs
- [ ] [USER-APPROVE] Approve milestone plan

---

## Branch Creation

**Checklist:**

- [ ] Update main branch (git pull)
- [ ] Create feature branch
- [ ] Verify branch creation

---

## Milestone Closing

**Checklist:**

- [ ] Run full test suite
- [ ] Merge to main branch
- [ ] Push to remote
- [ ] Update documentation

---

## Phase Planning

**Checklist:**

- [ ] Review PRD for phase objectives
- [ ] Define specific deliverables
- [ ] Update PRD if needed

---

## Phase Discussion

**Checklist:**

- [ ] Propose detailed design
- [ ] Discuss technical approach
- [ ] Identify risks or blockers
- [ ] [USER-APPROVE] Approve before spec

---

## Specification

**Checklist:**

- [ ] Create/update module structure
- [ ] Write technical spec (spec.md)
- [ ] Update related files section
- [ ] Check if architecture update needed

---

## Implementation

**Checklist:**

- [ ] Create files based on spec
- [ ] Implement logic following spec
- [ ] Verify imports and dependencies

---

## Testing

**Checklist:**

- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Run all tests

---

## Self-Review

**Checklist:**

- [ ] Check spec alignment
- [ ] Review error handling
- [ ] Verify code quality
- [ ] [USER-APPROVE] Approve for closing

---

## Phase Closing

**Checklist:**

- [ ] Update spec if deviated
- [ ] Record tech debt if any
- [ ] Git commit with message
- [ ] Update phase status
'''


def init_project(
    template: str = "simple",
    project_name: Optional[str] = None,
    with_claude_md: bool = True,
    with_guide: bool = True,
    force: bool = False
) -> str:
    """
    Initialize a new project with workflow configuration.

    Args:
        template: "simple" or "full"
        project_name: Project name for config
        with_claude_md: Create CLAUDE.md for AI instructions
        with_guide: Create PROJECT_MANAGEMENT_GUIDE.md
        force: Overwrite existing files

    Returns:
        Status message
    """
    results = []
    cwd = Path.cwd()

    # Detect project name
    if not project_name:
        project_name = cwd.name

    # 1. Create workflow.yaml
    workflow_path = cwd / "workflow.yaml"
    if workflow_path.exists() and not force:
        results.append(f"⚠️  workflow.yaml already exists (use --force to overwrite)")
    else:
        workflow_content = SIMPLE_WORKFLOW if template == "simple" else FULL_WORKFLOW
        workflow_content = workflow_content.format(project_name=project_name)
        workflow_path.write_text(workflow_content, encoding='utf-8')
        results.append(f"✅ Created workflow.yaml ({template} template)")

    # 2. Create .workflow/state.json
    workflow_dir = cwd / ".workflow"
    workflow_dir.mkdir(exist_ok=True)
    state_path = workflow_dir / "state.json"

    initial_stage = "START" if template == "simple" else "M0"
    if state_path.exists() and not force:
        results.append(f"⚠️  .workflow/state.json already exists")
    else:
        state_content = INITIAL_STATE.format(initial_stage=initial_stage)
        state_path.write_text(state_content, encoding='utf-8')
        results.append(f"✅ Created .workflow/state.json (stage: {initial_stage})")

    # 3. Create .memory/docs/PROJECT_MANAGEMENT_GUIDE.md
    if with_guide:
        memory_docs = cwd / ".memory" / "docs"
        memory_docs.mkdir(parents=True, exist_ok=True)
        guide_path = memory_docs / "PROJECT_MANAGEMENT_GUIDE.md"

        if guide_path.exists() and not force:
            results.append(f"⚠️  PROJECT_MANAGEMENT_GUIDE.md already exists")
        else:
            stage_docs = generate_stage_docs(template)
            guide_content = GUIDE_TEMPLATE.format(stage_docs=stage_docs)
            guide_path.write_text(guide_content, encoding='utf-8')
            results.append(f"✅ Created .memory/docs/PROJECT_MANAGEMENT_GUIDE.md")

    # 4. Create workflow instructions template
    if with_claude_md:
        template_path = workflow_dir / "WORKFLOW_INSTRUCTIONS.md"
        template_path.write_text(WORKFLOW_INSTRUCTIONS_TEMPLATE, encoding='utf-8')
        results.append(f"✅ Created .workflow/WORKFLOW_INSTRUCTIONS.md")

        claude_path = cwd / "CLAUDE.md"
        if claude_path.exists():
            # CLAUDE.md exists - provide guidance on what to add
            results.append("")
            results.append("📋 CLAUDE.md already exists. Add these lines:")
            results.append("-" * 50)
            results.append("1. At the TOP of CLAUDE.md, add:")
            results.append("   @import .memory/ACTIVE_STATUS.md")
            results.append("")
            results.append("2. Add the workflow section from:")
            results.append("   .workflow/WORKFLOW_INSTRUCTIONS.md")
            results.append("-" * 50)
        else:
            # No CLAUDE.md - create a minimal one
            minimal_claude = '''# AI Agent Instructions

@import .memory/ACTIVE_STATUS.md

## Workflow Protocol

> This project uses `workflow-tool`. Run `flow status` at the start of every turn.

**Quick Reference:**
- `flow status` - Check current stage and checklist
- `flow check N` - Mark item N as done
- `flow check N --evidence "..."` - Mark with justification
- `flow check N --token "..."` - For [USER-APPROVE] items
- `flow next` - Move to next stage

**Rules:**
1. Always run `flow status` first
2. State current stage: `**[Stage XX]** Name`
3. Complete checklist items in order
4. Never skip [USER-APPROVE] items

---

## Project Context

Project: {project_name}
'''
            claude_path.write_text(minimal_claude.format(project_name=project_name), encoding='utf-8')
            results.append(f"✅ Created CLAUDE.md (minimal template)")

    # 5. Create .gitignore entries suggestion
    gitignore_path = cwd / ".gitignore"
    gitignore_entries = """
# Workflow Tool
.workflow/secret
.workflow/audit.log
.memory/ACTIVE_STATUS.md
"""
    if gitignore_path.exists():
        content = gitignore_path.read_text()
        if ".workflow/secret" not in content:
            results.append(f"💡 Consider adding to .gitignore:\n{gitignore_entries}")
    else:
        results.append(f"💡 Create .gitignore with:\n{gitignore_entries}")

    # Summary
    results.append("")
    results.append("=" * 50)
    results.append(f"🎉 Project initialized with '{template}' workflow!")
    results.append("")
    results.append("Next steps:")
    results.append("  1. Run: flow status")
    results.append("  2. Run: flow secret-generate  (for USER-APPROVE)")
    results.append("  3. Start working through the checklist")
    results.append("")
    results.append("For AI assistants:")
    results.append("  - CLAUDE.md contains workflow instructions")
    results.append("  - AI should run 'flow status' at start of each session")

    return "\n".join(results)


def show_templates() -> str:
    """Show available templates."""
    return """Available Templates:

1. simple (default)
   - 4 stages: START → DEVELOP → REVIEW → DONE
   - Good for: Small projects, learning, quick tasks

2. full
   - Milestone stages: M0 → M1 → M2 → M3 → M4
   - Phase stages: P1 → P2 → P3 → P4 → P5 → P6 → P7
   - Good for: Large projects, team workflows

Usage:
  flow init                    # Use simple template
  flow init --template full    # Use full template
  flow init --template simple --name "My Project"
"""
