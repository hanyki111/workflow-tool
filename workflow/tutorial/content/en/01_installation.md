# Installation & Setup

This section covers how to install and configure the workflow tool.

## Installation

### Using pip (Recommended)

```bash
# Install in editable mode for development
pip install -e .

# Or install from package
pip install ai-workflow-engine
```

### Verify Installation

```bash
# Should display help message
flow --help

# Alternative invocation
python -m workflow --help
```

## Initial Configuration

### 1. Create workflow.yaml

The workflow configuration lives in `workflow.yaml` at your project root:

```yaml
version: "2.0"

variables:
  project_name: "my-project"

stages:
  M0:
    id: "M0"
    label: "Initial Stage"
    checklist:
      - "First item to complete"
      - "Second item to complete"
    transitions:
      - target: "M1"
```

### 2. Initialize State

Create `.workflow/state.json`:

```json
{
  "current_stage": "M0",
  "checklist": []
}
```

### 3. Set Up Shell Alias (Optional)

```bash
# Add to your .bashrc or .zshrc
alias flow='python -m workflow'

# Or use the built-in installer
flow install-alias --name flow
```

## Language Configuration

Set your preferred language:

```bash
# Via environment variable
export FLOW_LANG=ko

# Via command line
flow --lang ko status

# Via workflow.yaml
# Add: language: "ko"
```

## Directory Structure

After setup, your project should have:

```
my-project/
├── workflow.yaml        # Workflow definition
├── .workflow/
│   └── state.json       # Current state
└── .memory/             # Project knowledge (optional)
    └── docs/
        └── PROJECT_MANAGEMENT_GUIDE.md
```

Next: Learn about basic commands!
