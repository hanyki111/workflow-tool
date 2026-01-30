# Custom Plugins Example

Demonstrates how to create and use custom validators for workflow transitions.

## Overview

This example shows three custom validators:

1. **GitBranchValidator** - Ensure correct Git branch
2. **CoverageValidator** - Check test coverage threshold
3. **DependencyValidator** - Verify no security vulnerabilities

## File Structure

```
custom-plugins/
├── workflow.yaml           # Workflow using custom plugins
├── .workflow/
│   └── state.json
├── validators/
│   ├── __init__.py
│   └── custom.py           # Custom validator implementations
└── README.md
```

## Custom Validators

### 1. GitBranchValidator

Ensures you're on the correct Git branch before transitions:

```python
class GitBranchValidator(BaseValidator):
    def validate(self, args, context):
        expected = args.get('branch', 'main')
        result = subprocess.run(
            ['git', 'branch', '--show-current'],
            capture_output=True, text=True
        )
        current = result.stdout.strip()
        return current == expected
```

**Usage in workflow.yaml:**
```yaml
conditions:
  - rule: git_branch
    args:
      branch: "feature/my-feature"
    fail_message: "Must be on feature branch"
```

### 2. CoverageValidator

Checks that test coverage meets a minimum threshold:

```python
class CoverageValidator(BaseValidator):
    def validate(self, args, context):
        minimum = args.get('minimum', 80)
        # Run pytest with coverage
        result = subprocess.run(
            ['pytest', '--cov=src', '--cov-report=term', '--cov-fail-under=' + str(minimum)],
            capture_output=True
        )
        return result.returncode == 0
```

**Usage in workflow.yaml:**
```yaml
conditions:
  - rule: coverage
    args:
      minimum: 80
    fail_message: "Test coverage must be at least 80%"
```

### 3. DependencyValidator

Checks for security vulnerabilities in dependencies:

```python
class DependencyValidator(BaseValidator):
    def validate(self, args, context):
        # Run safety check (pip install safety)
        result = subprocess.run(
            ['safety', 'check', '--json'],
            capture_output=True
        )
        return result.returncode == 0
```

**Usage in workflow.yaml:**
```yaml
conditions:
  - rule: deps_secure
    fail_message: "Security vulnerabilities found in dependencies"
```

## Setup

### 1. Install Dependencies

```bash
# For coverage validation
pip install pytest-cov

# For dependency checking
pip install safety
```

### 2. Set Python Path

```bash
cd examples/custom-plugins
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### 3. Test the Workflow

```bash
flow status
flow check 1 2 3
flow next  # Will check custom validators
```

## Creating Your Own Validators

### Step 1: Create Validator Class

```python
# my_validators.py
from workflow.core.validator import BaseValidator

class MyValidator(BaseValidator):
    """
    Custom validator description.

    Args (from workflow.yaml):
        arg1: Description of arg1
        arg2: Description of arg2

    Context:
        project_root: Base directory path
    """

    def validate(self, args: dict, context: dict) -> bool:
        # Get arguments
        arg1 = args.get('arg1', 'default')
        project_root = context.get('project_root', '.')

        # Your validation logic
        try:
            # ... do checks ...
            return True  # Pass
        except Exception:
            return False  # Fail
```

### Step 2: Register in workflow.yaml

```yaml
plugins:
  my_check: "my_validators.MyValidator"
```

### Step 3: Use in Conditions

```yaml
stages:
  STAGE_NAME:
    transitions:
      - target: "NEXT_STAGE"
        conditions:
          - rule: my_check
            args:
              arg1: "value1"
              arg2: "value2"
            fail_message: "My validation failed"
```

## Validator Ideas

Here are some useful validators you might create:

| Validator | Purpose |
|-----------|---------|
| `DockerRunning` | Check if Docker daemon is running |
| `PortAvailable` | Verify a port is free |
| `EnvVarsSet` | Required environment variables exist |
| `APIHealthy` | External API health check |
| `DBMigrated` | Database migrations are up to date |
| `LintClean` | No linting errors |
| `TypeCheckPass` | mypy/pyright passes |
| `NoTODOs` | No TODO comments in code |
| `ChangelogUpdated` | CHANGELOG.md was modified |
| `VersionBumped` | Version number was incremented |

## Debugging Validators

### Test Validator Directly

```python
# test_validator.py
from validators.custom import GitBranchValidator

validator = GitBranchValidator()
result = validator.validate(
    args={'branch': 'main'},
    context={'project_root': '.'}
)
print(f"Validation result: {result}")
```

### Add Debug Output

```python
class MyValidator(BaseValidator):
    def validate(self, args, context):
        print(f"DEBUG: args={args}")
        print(f"DEBUG: context={context}")
        # ... rest of validation
```

### Check Plugin Loading

```bash
python -c "from validators.custom import GitBranchValidator; print('OK')"
```

## Best Practices

1. **Keep validators focused**: One check per validator
2. **Handle exceptions**: Don't let validators crash
3. **Provide clear fail_message**: Help users understand what failed
4. **Make validators fast**: Avoid long-running operations
5. **Use context wisely**: `project_root` is always available
6. **Document args**: Clear documentation for workflow.yaml users

## Troubleshooting

### "Failed to load plugin"

```bash
# Check module path
python -c "from validators.custom import MyValidator"

# Verify PYTHONPATH
echo $PYTHONPATH
```

### Validator Always Fails

```bash
# Test the underlying command manually
pytest --cov=src --cov-fail-under=80

# Check validator logic
python -c "
from validators.custom import CoverageValidator
v = CoverageValidator()
print(v.validate({'minimum': 80}, {}))
"
```

### Validator Always Passes

Ensure you're returning `False` for failure cases:
```python
def validate(self, args, context):
    if something_wrong:
        return False  # Must explicitly return False
    return True
```
