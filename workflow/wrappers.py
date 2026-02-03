"""Shell wrapper generation for automatic workflow integration.

This module generates shell functions that wrap CLI commands to automatically
call `flow check --tag` when commands succeed.
"""

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

from .i18n import t


# Pattern to match [CMD:command] or [CMD:command:subcommand] tags in checklist items
CMD_TAG_PATTERN = re.compile(r'\[CMD:([\w_-]+)(?::([\w_-]+))?\]')


@dataclass
class WrapperSpec:
    """Specification for a shell wrapper."""
    command: str           # Base command (e.g., "pytest", "memory_tool")
    subcommand: Optional[str]  # Optional subcommand (e.g., "write")
    tag: str               # Full tag (e.g., "CMD:pytest" or "CMD:memory_tool:write")
    stage: str             # Stage ID where this tag appears
    text: str              # Full checklist item text


def extract_tags(config_path: str = "workflow.yaml") -> list[WrapperSpec]:
    """Extract all [CMD:xxx] tags from workflow.yaml.

    Args:
        config_path: Path to workflow.yaml

    Returns:
        List of WrapperSpec objects for each unique command/tag combination
    """
    if not os.path.exists(config_path):
        return []

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    if not config or 'stages' not in config:
        return []

    specs: list[WrapperSpec] = []
    seen_tags: set[str] = set()

    for stage_id, stage_data in config.get('stages', {}).items():
        checklist = stage_data.get('checklist', [])
        for item in checklist:
            # Handle both string items and dict items (ChecklistItemConfig)
            text = item if isinstance(item, str) else item.get('text', '')

            match = CMD_TAG_PATTERN.search(text)
            if match:
                command = match.group(1)
                subcommand = match.group(2)  # May be None

                if subcommand:
                    tag = f"CMD:{command}:{subcommand}"
                else:
                    tag = f"CMD:{command}"

                # Avoid duplicates
                if tag not in seen_tags:
                    seen_tags.add(tag)
                    specs.append(WrapperSpec(
                        command=command,
                        subcommand=subcommand,
                        tag=tag,
                        stage=stage_id,
                        text=text
                    ))

    return specs


def detect_shell() -> str:
    """Detect the current shell environment.

    Returns:
        Shell name: 'bash', 'zsh', 'powershell', 'cmd', or 'fish'
    """
    if sys.platform == 'win32':
        # Check if running in CMD or PowerShell
        # PSModulePath is typically set in PowerShell
        if os.environ.get('PSModulePath'):
            return 'powershell'
        return 'cmd'

    shell = os.environ.get('SHELL', '')
    if 'zsh' in shell:
        return 'zsh'
    elif 'fish' in shell:
        return 'fish'
    return 'bash'


def get_shell_config_path(shell: str) -> Optional[Path]:
    """Get the path to shell configuration file.

    Args:
        shell: Shell name (bash, zsh, powershell, fish, cmd)

    Returns:
        Path to config file, or None if not found/applicable
    """
    home = Path.home()

    if shell == 'bash':
        for name in ['.bashrc', '.bash_profile']:
            path = home / name
            if path.exists():
                return path
        # Default to .bashrc even if it doesn't exist
        return home / '.bashrc'

    elif shell == 'zsh':
        return home / '.zshrc'

    elif shell == 'fish':
        config_dir = home / '.config' / 'fish'
        return config_dir / 'config.fish'

    elif shell == 'powershell':
        # PowerShell profile path varies by platform
        if sys.platform == 'win32':
            # Windows PowerShell or PowerShell Core
            docs = Path(os.environ.get('USERPROFILE', '')) / 'Documents'
            ps_dir = docs / 'WindowsPowerShell'
            if not ps_dir.exists():
                ps_dir = docs / 'PowerShell'
            return ps_dir / 'Microsoft.PowerShell_profile.ps1'
        else:
            # PowerShell Core on Unix
            return home / '.config' / 'powershell' / 'Microsoft.PowerShell_profile.ps1'

    elif shell == 'cmd':
        # CMD doesn't have a standard config file
        # Wrappers are installed as batch files in PATH
        return None

    return None


def get_wrapper_file_path(shell: str) -> Path:
    """Get the path where wrapper file will be created.

    Args:
        shell: Shell name

    Returns:
        Path to wrapper file in .workflow directory
        For CMD, returns directory path where .bat files will be created
    """
    if shell == 'cmd':
        # CMD uses individual .bat files in a directory
        return Path('.workflow') / 'wrappers'
    ext = 'ps1' if shell == 'powershell' else 'sh'
    return Path('.workflow') / f'wrappers.{ext}'


def generate_bash_wrapper(spec: WrapperSpec) -> str:
    """Generate bash/zsh wrapper function.

    Args:
        spec: WrapperSpec for the command

    Returns:
        Shell function definition
    """
    if spec.subcommand:
        # Subcommand-specific wrapper
        return f'''
{spec.command}() {{
    command {spec.command} "$@"
    local result=$?
    if [ $result -eq 0 ]; then
        case "$1" in
            {spec.subcommand}) flow check --tag "{spec.tag}" --evidence "Auto: exit 0" 2>/dev/null ;;
        esac
    fi
    return $result
}}
'''
    else:
        # Simple command wrapper
        return f'''
{spec.command}() {{
    command {spec.command} "$@"
    local result=$?
    [ $result -eq 0 ] && flow check --tag "{spec.tag}" --evidence "Auto: exit 0" 2>/dev/null
    return $result
}}
'''


def generate_powershell_wrapper(spec: WrapperSpec) -> str:
    """Generate PowerShell wrapper function.

    Args:
        spec: WrapperSpec for the command

    Returns:
        PowerShell function definition
    """
    # Create a valid PowerShell function name
    func_name = f"Invoke-{spec.command.title().replace('_', '')}Wrapper"

    if spec.subcommand:
        return f'''
function {func_name} {{
    param([Parameter(ValueFromRemainingArguments)]$WrapperArgs)
    & {spec.command} @WrapperArgs
    if ($LASTEXITCODE -eq 0 -and $WrapperArgs[0] -eq "{spec.subcommand}") {{
        & flow check --tag "{spec.tag}" --evidence "Auto: exit 0" 2>$null
    }}
    exit $LASTEXITCODE
}}
Set-Alias -Name {spec.command} -Value {func_name} -Force
'''
    else:
        return f'''
function {func_name} {{
    param([Parameter(ValueFromRemainingArguments)]$WrapperArgs)
    & {spec.command} @WrapperArgs
    if ($LASTEXITCODE -eq 0) {{
        & flow check --tag "{spec.tag}" --evidence "Auto: exit 0" 2>$null
    }}
    exit $LASTEXITCODE
}}
Set-Alias -Name {spec.command} -Value {func_name} -Force
'''


def generate_fish_wrapper(spec: WrapperSpec) -> str:
    """Generate fish shell wrapper function.

    Args:
        spec: WrapperSpec for the command

    Returns:
        Fish function definition
    """
    if spec.subcommand:
        return f'''
function {spec.command} --wraps {spec.command}
    command {spec.command} $argv
    set -l result $status
    if test $result -eq 0; and test "$argv[1]" = "{spec.subcommand}"
        flow check --tag "{spec.tag}" --evidence "Auto: exit 0" 2>/dev/null
    end
    return $result
end
'''
    else:
        return f'''
function {spec.command} --wraps {spec.command}
    command {spec.command} $argv
    set -l result $status
    if test $result -eq 0
        flow check --tag "{spec.tag}" --evidence "Auto: exit 0" 2>/dev/null
    end
    return $result
end
'''


def generate_cmd_wrapper(spec: WrapperSpec) -> str:
    """Generate Windows CMD batch file wrapper.

    Args:
        spec: WrapperSpec for the command

    Returns:
        Batch file content
    """
    if spec.subcommand:
        return f'''@echo off
setlocal
rem AI Workflow Tool wrapper for {spec.command} ({spec.tag})

rem Call original command (assumes .exe is in PATH after wrapper dir)
call {spec.command}.exe %*
set _exitcode=%ERRORLEVEL%

if %_exitcode% EQU 0 (
    if /i "%~1"=="{spec.subcommand}" (
        call flow check --tag "{spec.tag}" --evidence "Auto: exit 0" 2>nul
    )
)
exit /b %_exitcode%
'''
    else:
        return f'''@echo off
setlocal
rem AI Workflow Tool wrapper for {spec.command} ({spec.tag})

rem Call original command (assumes .exe is in PATH after wrapper dir)
call {spec.command}.exe %*
set _exitcode=%ERRORLEVEL%

if %_exitcode% EQU 0 (
    call flow check --tag "{spec.tag}" --evidence "Auto: exit 0" 2>nul
)
exit /b %_exitcode%
'''


def generate_cmd_wrappers(specs: list[WrapperSpec]) -> dict[str, str]:
    """Generate CMD batch files for each command.

    Args:
        specs: List of WrapperSpec objects

    Returns:
        Dict mapping filename to file content
    """
    # Group specs by command for subcommand handling
    commands: dict[str, list[WrapperSpec]] = {}
    for spec in specs:
        if spec.command not in commands:
            commands[spec.command] = []
        commands[spec.command].append(spec)

    files: dict[str, str] = {}
    for cmd, cmd_specs in commands.items():
        # For CMD, we create one .bat file per command
        # that handles all subcommands
        if len(cmd_specs) == 1 and cmd_specs[0].subcommand is None:
            files[f"{cmd}.bat"] = generate_cmd_wrapper(cmd_specs[0])
        else:
            # Generate combined wrapper with all subcommands
            files[f"{cmd}.bat"] = generate_cmd_combined_wrapper(cmd, cmd_specs)

    return files


def generate_cmd_combined_wrapper(command: str, specs: list[WrapperSpec]) -> str:
    """Generate CMD wrapper for command with multiple subcommands.

    Args:
        command: Base command name
        specs: List of specs for this command

    Returns:
        Batch file content
    """
    cases = []
    for spec in specs:
        if spec.subcommand:
            cases.append(f'if /i "%~1"=="{spec.subcommand}" call flow check --tag "{spec.tag}" --evidence "Auto: exit 0" 2>nul')

    case_block = '\n    '.join(cases)

    return f'''@echo off
setlocal
rem AI Workflow Tool wrapper for {command}

rem Call original command
call {command}.exe %*
set _exitcode=%ERRORLEVEL%

if %_exitcode% EQU 0 (
    {case_block}
)
exit /b %_exitcode%
'''


def generate_wrappers_file(specs: list[WrapperSpec], shell: str) -> str:
    """Generate complete wrappers file content.

    Args:
        specs: List of WrapperSpec objects
        shell: Target shell

    Returns:
        Complete file content (not used for CMD - use generate_cmd_wrappers instead)
    """
    # Group specs by command for subcommand handling
    commands: dict[str, list[WrapperSpec]] = {}
    for spec in specs:
        if spec.command not in commands:
            commands[spec.command] = []
        commands[spec.command].append(spec)

    if shell == 'powershell':
        header = "# AI Workflow Tool - Auto-generated wrappers\n# Do not edit manually\n"
        generators = []
        for cmd, cmd_specs in commands.items():
            # If there are multiple specs for same command, merge subcommands
            if len(cmd_specs) == 1 and cmd_specs[0].subcommand is None:
                generators.append(generate_powershell_wrapper(cmd_specs[0]))
            else:
                # Generate wrapper with all subcommands
                for spec in cmd_specs:
                    generators.append(generate_powershell_wrapper(spec))
        return header + '\n'.join(generators)

    elif shell == 'fish':
        header = "# AI Workflow Tool - Auto-generated wrappers\n# Do not edit manually\n"
        generators = []
        for cmd, cmd_specs in commands.items():
            if len(cmd_specs) == 1 and cmd_specs[0].subcommand is None:
                generators.append(generate_fish_wrapper(cmd_specs[0]))
            else:
                for spec in cmd_specs:
                    generators.append(generate_fish_wrapper(spec))
        return header + '\n'.join(generators)

    else:  # bash/zsh
        header = "#!/bin/bash\n# AI Workflow Tool - Auto-generated wrappers\n# Do not edit manually\n"
        generators = []
        for cmd, cmd_specs in commands.items():
            if len(cmd_specs) == 1 and cmd_specs[0].subcommand is None:
                generators.append(generate_bash_wrapper(cmd_specs[0]))
            else:
                # For commands with subcommands, generate a combined wrapper
                generators.append(generate_bash_combined_wrapper(cmd, cmd_specs))
        return header + '\n'.join(generators)


def generate_bash_combined_wrapper(command: str, specs: list[WrapperSpec]) -> str:
    """Generate bash wrapper for command with multiple subcommands.

    Args:
        command: Base command name
        specs: List of specs for this command (may include subcommand variants)

    Returns:
        Combined shell function
    """
    # Build case statement for subcommands
    cases = []
    simple_tag = None

    for spec in specs:
        if spec.subcommand:
            cases.append(f'            {spec.subcommand}) flow check --tag "{spec.tag}" --evidence "Auto: exit 0" 2>/dev/null ;;')
        else:
            simple_tag = spec.tag

    if cases:
        case_block = '\n'.join(cases)
        wrapper = f'''
{command}() {{
    command {command} "$@"
    local result=$?
    if [ $result -eq 0 ]; then
        case "$1" in
{case_block}
        esac
    fi
    return $result
}}
'''
    else:
        # No subcommands, simple wrapper
        wrapper = f'''
{command}() {{
    command {command} "$@"
    local result=$?
    [ $result -eq 0 ] && flow check --tag "{simple_tag}" --evidence "Auto: exit 0" 2>/dev/null
    return $result
}}
'''
    return wrapper


def get_source_line(wrapper_path: Path, shell: str) -> str:
    """Get the line to add to shell config to source wrappers.

    Args:
        wrapper_path: Path to wrappers file
        shell: Shell name

    Returns:
        Source line to add to config
    """
    abs_path = wrapper_path.resolve()

    if shell == 'powershell':
        return f'. "{abs_path}"'
    elif shell == 'fish':
        return f'source "{abs_path}"'
    else:  # bash/zsh
        return f'source "{abs_path}"'


def install_wrappers(
    shell: Optional[str] = None,
    dry_run: bool = False,
    config_path: str = "workflow.yaml"
) -> str:
    """Install shell wrappers for workflow integration.

    Args:
        shell: Target shell (auto-detect if None)
        dry_run: If True, only preview changes
        config_path: Path to workflow.yaml

    Returns:
        Status message
    """
    # Auto-detect shell if not specified
    if shell is None or shell == 'auto':
        shell = detect_shell()

    output = [t('wrappers.detected_shell', shell=shell)]

    # Extract tags
    specs = extract_tags(config_path)
    if not specs:
        return t('wrappers.no_tags')

    output.append(t('wrappers.found_tags', count=len(specs)))
    for spec in specs:
        output.append(f"  - {spec.command}" + (f":{spec.subcommand}" if spec.subcommand else "") + f" ({spec.stage})")

    wrapper_path = get_wrapper_file_path(shell)

    # CMD uses separate batch files
    if shell == 'cmd':
        cmd_files = generate_cmd_wrappers(specs)

        if dry_run:
            output.append("")
            output.append(t('wrappers.dry_run_header'))
            output.append(f"  {t('wrappers.would_create', path=str(wrapper_path) + '/')}")
            for filename in cmd_files:
                output.append(f"    - {filename}")
            output.append("")
            output.append(t('wrappers.cmd_path_hint', path=str(wrapper_path.resolve())))
            output.append("")
            output.append(t('wrappers.wrapper_preview'))
            output.append("-" * 40)
            for filename, content in cmd_files.items():
                output.append(f"=== {filename} ===")
                output.append(content)
            output.append("-" * 40)
            return '\n'.join(output)

        # Create wrapper directory
        wrapper_path.mkdir(parents=True, exist_ok=True)

        output.append("")
        output.append(t('wrappers.generating'))

        for filename, content in cmd_files.items():
            file_path = wrapper_path / filename
            file_path.write_text(content, encoding='utf-8')
            output.append(t('wrappers.created', path=str(file_path)))

        output.append("")
        output.append(t('wrappers.cmd_path_hint', path=str(wrapper_path.resolve())))
        output.append(t('wrappers.cmd_path_instruction'))

        return '\n'.join(output)

    # Other shells use single wrapper file
    wrapper_content = generate_wrappers_file(specs, shell)
    config_file = get_shell_config_path(shell)
    source_line = get_source_line(wrapper_path, shell)

    if dry_run:
        output.append("")
        output.append(t('wrappers.dry_run_header'))
        output.append(f"  {t('wrappers.would_create', path=str(wrapper_path))}")
        if config_file:
            output.append(f"  {t('wrappers.would_add_source', config=str(config_file))}")
        output.append("")
        output.append(t('wrappers.wrapper_preview'))
        output.append("-" * 40)
        output.append(wrapper_content)
        output.append("-" * 40)
        return '\n'.join(output)

    # Create .workflow directory if needed
    wrapper_path.parent.mkdir(parents=True, exist_ok=True)

    # Write wrapper file
    output.append("")
    output.append(t('wrappers.generating'))
    wrapper_path.write_text(wrapper_content, encoding='utf-8')
    output.append(t('wrappers.created', path=str(wrapper_path)))

    # Add source line to shell config
    if config_file:
        if config_file.exists():
            content = config_file.read_text(encoding='utf-8')
            marker = "# AI Workflow wrappers"

            if marker in content or str(wrapper_path) in content:
                output.append(t('wrappers.source_exists', config=str(config_file)))
            else:
                with open(config_file, 'a', encoding='utf-8') as f:
                    f.write(f"\n{marker}\n{source_line}\n")
                output.append(t('wrappers.source_added', config=str(config_file)))
        else:
            # Create config file with source line
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text(f"# AI Workflow wrappers\n{source_line}\n", encoding='utf-8')
            output.append(t('wrappers.source_added', config=str(config_file)))

    output.append("")
    if config_file:
        output.append(t('wrappers.success', config=str(config_file)))

    return '\n'.join(output)


def uninstall_wrappers(shell: Optional[str] = None) -> str:
    """Remove installed shell wrappers.

    Args:
        shell: Target shell (auto-detect if None)

    Returns:
        Status message
    """
    if shell is None or shell == 'auto':
        shell = detect_shell()

    output = [t('wrappers.detected_shell', shell=shell)]

    wrapper_path = get_wrapper_file_path(shell)
    config_file = get_shell_config_path(shell)

    # CMD uses a directory of batch files
    if shell == 'cmd':
        if wrapper_path.exists() and wrapper_path.is_dir():
            import shutil
            shutil.rmtree(wrapper_path)
            output.append(t('wrappers.removed', path=str(wrapper_path)))
        else:
            output.append(t('wrappers.not_found', path=str(wrapper_path)))
        output.append(t('wrappers.cmd_path_remove_hint'))
        return '\n'.join(output)

    # Remove wrapper file
    if wrapper_path.exists():
        wrapper_path.unlink()
        output.append(t('wrappers.removed', path=str(wrapper_path)))
    else:
        output.append(t('wrappers.not_found', path=str(wrapper_path)))

    # Remove source line from config
    if config_file and config_file.exists():
        content = config_file.read_text(encoding='utf-8')
        marker = "# AI Workflow wrappers"

        if marker in content:
            # Remove the marker and following source line
            lines = content.split('\n')
            new_lines = []
            skip_next = False

            for line in lines:
                if marker in line:
                    skip_next = True
                    continue
                if skip_next and ('wrappers' in line.lower() or line.strip() == ''):
                    if 'wrappers' in line.lower():
                        skip_next = False
                    continue
                skip_next = False
                new_lines.append(line)

            # Remove trailing empty lines that may have been left
            while new_lines and new_lines[-1].strip() == '':
                new_lines.pop()

            config_file.write_text('\n'.join(new_lines) + '\n', encoding='utf-8')
            output.append(t('wrappers.uninstalled', config=str(config_file)))
        else:
            output.append(t('wrappers.no_source_found', config=str(config_file)))

    return '\n'.join(output)


def list_wrappers(config_path: str = "workflow.yaml") -> str:
    """List wrappers that would be generated.

    Args:
        config_path: Path to workflow.yaml

    Returns:
        Formatted list of wrappers
    """
    specs = extract_tags(config_path)

    if not specs:
        return t('wrappers.no_tags')

    output = [t('wrappers.list_header')]
    for spec in specs:
        cmd_display = spec.command
        if spec.subcommand:
            cmd_display += f" {spec.subcommand}"
        output.append(t('wrappers.list_item', cmd=cmd_display, tag=spec.tag))

    return '\n'.join(output)
