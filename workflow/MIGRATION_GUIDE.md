# Workflow Tool Migration Guide

This document describes how to extract the `tools/workflow` directory into a standalone repository (e.g., `guardian-cli` or `flow-tool`).

## 1. Extraction Steps

### A. Copy Files
Copy the entire `tools/workflow` directory to the root of your new repository.

```bash
cp -r /path/to/text-rpg/tools/workflow /path/to/new-repo/src
```

### B. Directory Restructuring
Recommended structure for the standalone project:

```text
new-repo/
├── src/
│   └── workflow/          # Renamed from tools/workflow
│       ├── __init__.py
│       ├── cli.py
│       └── core/
├── tests/                 # Copy unit tests
├── workflow.yaml          # Copy from templates/default_workflow.yaml
├── setup.py               # Create new
└── README.md
```

### C. Dependency Management
Create a `requirements.txt` or `pyproject.toml`.
Required dependencies:
- `PyYAML`
- `argparse` (Standard lib)
- `dataclasses` (Standard lib)

## 2. Configuration Setup

1. Copy `templates/default_workflow.yaml` to your project root as `workflow.yaml`.
2. Edit `workflow.yaml`:
   - `guide_file`: Point to your project's main documentation (e.g., `CONTRIBUTING.md` or `GUIDE.md`).
   - `hierarchy`: Define your project's levels (e.g., `["sprint", "task"]`).
   - `mappings`: Map your document headers to stage codes.
   - `sequence`: Define the flow of states.

## 3. Alias Installation

Run the installer to set up the `flow` command (or your preferred name).

```bash
python src/workflow/cli.py install-alias --name myflow
```

## 4. Troubleshooting

- **Import Errors:** If you move `cli.py`, ensure `sys.path` allows importing `core`. The current `cli.py` appends `../../` to sys.path assuming it is in `tools/workflow/`. You may need to adjust this in a standalone package structure.
