# Milestone 42: State-Based Workflow Tool (Guardian)

> **"A Tool needed to build the Tool."**
> A configurable, state-based workflow enforcer to prevent process drift and reduce cognitive load.

## 1. Objectives
- **Rule Enforcement:** Enforce workflow steps (checklists, transitions) via code constraints.
- **Configurable Hierarchy:** Support various project structures (e.g., M-P-S, Sprint-Task) via `workflow.yaml`.
- **Context Persistence:** Store the current working state in a file (`.workflow/state.json`) to eliminate memory dependency.

## 2. Success Criteria
- **Generic Design:** The tool code itself must not contain hardcoded project terms (like "Text RPG", "M41").
- **Hierarchy Support:** Must verify that the tool can handle the complex "Milestone -> Phase -> Stage" structure of this project.
- **Blocking Mechanism:** `workflow next` must fail if the current stage's checklist is incomplete.

## 3. Architecture Strategy
- **In-Repo Incubation:** Developed in `tools/workflow/` but designed as a standalone generic tool.
- **Markdown-Driven:** Uses existing human-readable guide files as the source of truth for checklists.
- **Config-Driven:** Hierarchy, file paths, and mapping rules are defined in YAML.

## 4. Phase Breakdown

### Phase 42.1: Core Logic & Configuration
**Goal:** Build the engine that understands hierarchy and state.
- **Tasks:**
  - Define `WorkflowConfig` (YAML loader) to parse hierarchy definitions.
  - Implement `WorkflowState` (JSON manager) for persistence.
  - Implement `GuideParser` to extract checklists from Markdown based on header mappings.

### Phase 42.2: CLI Interface & Logic
**Goal:** Implement the user interface (CLI).
- **Tasks:**
  - `cli.py`: Implement commands (`status`, `next`, `check`, `jump`).
  - `Controller`: Handle state transitions and validation logic.
  - **Feature:** "Next" logic that calculates the next state based on hierarchy depth.

### Phase 42.3: Integration & Dogfooding ✅
**Goal:** Apply the tool to the current project.
- **Tasks:**
  - ✅ Create `workflow.yaml` for Text RPG Project.
  - ✅ Initialize `.workflow/state.json` with current M42 status.
  - ✅ Refine `PROJECT_MANAGEMENT_GUIDE.md` headers if necessary for better parsing.
  - ✅ Verify full cycle usage (Check -> Next -> Stage Change).

### Phase 42.4: Alias Feature & Enforcement ✅
**Goal:** Improve usability and ensure agent compliance.
- **Tasks:**
  - ✅ Implement `install-alias` command (Default name: `flow`).
  - ✅ Add "MANDATORY PROTOCOL" to `PROJECT_MANAGEMENT_GUIDE.md`.
  - ✅ Verify alias duplication logic.

### Version 1.1 - Multi-Check & Cognitive Hook ✅ (2026-01-28)
**Goal:** Enhance usability and prevent agent memory drift (TD-004).
- **Tasks:**
  - ✅ Implement **Multi-Check** support (`flow check 1 2 3`).
  - ✅ Implement **Cognitive Hook**: Automatically update `.memory/ACTIVE_STATUS.md` with current stage and checklist.
  - ✅ Implement **Auto-Status on Transition**: Next stage's checklist is displayed immediately after state change.
  - ✅ Add `--oneline` flag to `status` command for shell integration.

## 5. Dependencies
- Standard Python libraries (`argparse`, `json`, `re`) + `PyYAML` (already in requirements).
