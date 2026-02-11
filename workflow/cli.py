import argparse
import sys
import os
import io

import yaml

# Fix Windows console encoding for Unicode (emoji) support
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from .core.controller import WorkflowController
from .core.auth import generate_secret_interactive
from .i18n import t, set_language
from .i18n.detector import detect_language
from .tutorial import run_tutorial
from .init import init_project, show_templates
from .wrappers import install_wrappers, uninstall_wrappers, list_wrappers


def main():
    # Pre-parse for --lang flag to set language before building help text
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--lang", "-l", help="Set display language (en, ko)")
    pre_args, _ = pre_parser.parse_known_args()

    # Read language from workflow.yaml if it exists
    config_lang = None
    if os.path.exists("workflow.yaml"):
        try:
            with open("workflow.yaml", 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                if config:
                    config_lang = config.get('language')
        except Exception:
            pass  # Ignore errors, fall back to other detection methods

    # Detect and set language (CLI > env > config > locale > default)
    lang = detect_language(cli_lang=pre_args.lang, config_lang=config_lang)
    set_language(lang)

    # Main parser with localized help
    parser = argparse.ArgumentParser(
        description=t('help.main.description'),
        parents=[pre_parser]
    )
    subparsers = parser.add_subparsers(dest="command")

    # Status
    status_parser = subparsers.add_parser(
        "status",
        aliases=["s"],
        help=t('help.status.description')
    )
    status_parser.add_argument(
        "--oneline",
        action="store_true",
        help=t('help.status.oneline')
    )
    status_parser.add_argument(
        "--track",
        help=t('help.track.track_option')
    )
    status_parser.add_argument(
        "--all",
        action="store_true",
        dest="all_tracks",
        help=t('help.track.all_option')
    )

    # Next
    next_parser = subparsers.add_parser(
        "next",
        help=t('help.next.description')
    )
    next_parser.add_argument(
        "target",
        nargs="?",
        help=t('help.next.target')
    )
    next_parser.add_argument(
        "--force",
        action="store_true",
        help=t('help.next.force')
    )
    next_parser.add_argument(
        "--reason",
        default="",
        help=t('help.next.reason')
    )
    next_parser.add_argument(
        "--token", "-k",
        help=t('help.next.token')
    )
    next_parser.add_argument(
        "--skip-conditions",
        action="store_true",
        help=t('help.next.skip_conditions')
    )
    next_parser.add_argument(
        "--track",
        help=t('help.track.track_option')
    )

    # Check
    check_parser = subparsers.add_parser(
        "check",
        aliases=["c"],
        help=t('help.check.description'),
        epilog=t('help.check.epilog'),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    check_parser.add_argument(
        "indices",
        type=int,
        nargs="*",  # Optional when using --tag
        help=t('help.check.indices')
    )
    check_parser.add_argument(
        "--tag", "-t",
        help=t('help.check.tag')
    )
    check_parser.add_argument(
        "--token", "-k",
        help=t('help.check.token')
    )
    check_parser.add_argument(
        "--evidence", "-e",
        help=t('help.check.evidence')
    )
    check_parser.add_argument(
        "--args", "-a",
        help=t('help.check.args')
    )
    check_parser.add_argument(
        "--skip-action",
        action="store_true",
        help=t('help.check.skip_action')
    )
    check_parser.add_argument(
        "--agent",
        help=t('help.check.agent')
    )
    check_parser.add_argument(
        "--track",
        help=t('help.track.track_option')
    )

    # Uncheck
    uncheck_parser = subparsers.add_parser(
        "uncheck",
        aliases=["u"],
        help=t('help.uncheck.description')
    )
    uncheck_parser.add_argument(
        "indices",
        type=int,
        nargs="+",
        help=t('help.uncheck.indices')
    )
    uncheck_parser.add_argument(
        "--token", "-k",
        help=t('help.uncheck.token')
    )
    uncheck_parser.add_argument(
        "--track",
        help=t('help.track.track_option')
    )

    # Set
    set_parser = subparsers.add_parser(
        "set",
        help=t('help.set.description')
    )
    set_parser.add_argument(
        "stage",
        help=t('help.set.stage')
    )
    set_parser.add_argument(
        "--module",
        help=t('help.set.module')
    )
    set_parser.add_argument(
        "--force",
        action="store_true",
        help=t('help.set.force')
    )
    set_parser.add_argument(
        "--token", "-k",
        help=t('help.set.token')
    )
    set_parser.add_argument(
        "--track",
        help=t('help.track.track_option')
    )

    # Review
    review_parser = subparsers.add_parser(
        "review",
        help=t('help.review.description')
    )
    review_parser.add_argument(
        "--agent",
        required=True,
        help=t('help.review.agent')
    )
    review_parser.add_argument(
        "--summary",
        required=True,
        help=t('help.review.summary')
    )

    # Secret Generate
    subparsers.add_parser(
        "secret-generate",
        help=t('help.secret_generate.description')
    )

    # Module (subcommand group)
    module_parser = subparsers.add_parser(
        "module",
        help=t('help.module.description')
    )
    module_subparsers = module_parser.add_subparsers(dest="module_command")
    module_set_parser = module_subparsers.add_parser(
        "set",
        help=t('help.module.set')
    )
    module_set_parser.add_argument(
        "name",
        help=t('help.module.name')
    )
    module_set_parser.add_argument(
        "--track",
        help=t('help.track.track_option')
    )

    # Track (subcommand group)
    track_parser = subparsers.add_parser(
        "track",
        help=t('help.track.description')
    )
    track_subparsers = track_parser.add_subparsers(dest="track_command")

    # track create
    track_create_parser = track_subparsers.add_parser(
        "create",
        help=t('help.track.create')
    )
    track_create_parser.add_argument(
        "id",
        help=t('help.track.id')
    )
    track_create_parser.add_argument(
        "--label",
        required=True,
        help=t('help.track.label')
    )
    track_create_parser.add_argument(
        "--module",
        required=True,
        help=t('help.track.module')
    )
    track_create_parser.add_argument(
        "--stage",
        help=t('help.track.stage')
    )

    # track list
    track_subparsers.add_parser(
        "list",
        help=t('help.track.list')
    )

    # track switch
    track_switch_parser = track_subparsers.add_parser(
        "switch",
        help=t('help.track.switch')
    )
    track_switch_parser.add_argument(
        "id",
        help=t('help.track.id')
    )

    # track join
    track_join_parser = track_subparsers.add_parser(
        "join",
        help=t('help.track.join')
    )
    track_join_parser.add_argument(
        "--force",
        action="store_true",
        help=t('help.track.force')
    )
    track_join_parser.add_argument(
        "--token", "-k",
        help=t('help.track.token')
    )

    # track delete
    track_delete_parser = track_subparsers.add_parser(
        "delete",
        help=t('help.track.delete')
    )
    track_delete_parser.add_argument(
        "id",
        help=t('help.track.id')
    )

    # Phase (subcommand group)
    phase_parser = subparsers.add_parser(
        "phase",
        help=t('help.phase.description')
    )
    phase_subparsers = phase_parser.add_subparsers(dest="phase_command")

    # phase add
    phase_add_parser = phase_subparsers.add_parser(
        "add",
        help=t('help.phase.add')
    )
    phase_add_parser.add_argument(
        "id",
        help=t('help.phase.id')
    )
    phase_add_parser.add_argument(
        "--label",
        required=True,
        help=t('help.phase.label')
    )
    phase_add_parser.add_argument(
        "--module",
        required=True,
        help=t('help.phase.module')
    )
    phase_add_parser.add_argument(
        "--depends-on",
        default="",
        help=t('help.phase.depends_on')
    )

    # phase list
    phase_subparsers.add_parser(
        "list",
        help=t('help.phase.list')
    )

    # phase graph
    phase_subparsers.add_parser(
        "graph",
        help=t('help.phase.graph')
    )

    # phase remove
    phase_remove_parser = phase_subparsers.add_parser(
        "remove",
        help=t('help.phase.remove')
    )
    phase_remove_parser.add_argument(
        "id",
        help=t('help.phase.id')
    )

    # Alias Install
    alias_parser = subparsers.add_parser(
        "install-alias",
        help=t('help.install_alias.description')
    )
    alias_parser.add_argument(
        "--name",
        default="flow",
        help=t('help.install_alias.name')
    )

    # Tutorial
    tutorial_parser = subparsers.add_parser(
        "tutorial",
        aliases=["guide"],
        help=t('help.tutorial.description')
    )
    tutorial_parser.add_argument(
        "--list", "-L",
        action="store_true",
        help=t('help.tutorial.list')
    )
    tutorial_parser.add_argument(
        "--section", "-s",
        type=int,
        help=t('help.tutorial.section')
    )
    tutorial_parser.add_argument(
        "section_name",
        nargs="?",
        help=t('help.tutorial.section_name')
    )

    # Init
    init_parser = subparsers.add_parser(
        "init",
        help=t('help.init.description')
    )
    init_parser.add_argument(
        "--template", "-t",
        choices=["simple", "full"],
        default="simple",
        help=t('help.init.template')
    )
    init_parser.add_argument(
        "--name", "-n",
        help=t('help.init.name')
    )
    init_parser.add_argument(
        "--no-claude-md",
        action="store_true",
        help=t('help.init.no_claude_md')
    )
    init_parser.add_argument(
        "--no-guide",
        action="store_true",
        help=t('help.init.no_guide')
    )
    init_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help=t('help.init.force')
    )
    init_parser.add_argument(
        "--list-templates",
        action="store_true",
        help=t('help.init.list_templates')
    )

    # Install Wrappers
    wrappers_parser = subparsers.add_parser(
        "install-wrappers",
        help=t('help.install_wrappers.description')
    )
    wrappers_parser.add_argument(
        "--shell",
        choices=["bash", "zsh", "powershell", "cmd", "fish", "auto"],
        default="auto",
        help=t('help.install_wrappers.shell')
    )
    wrappers_parser.add_argument(
        "--list", "-L",
        action="store_true",
        help=t('help.install_wrappers.list')
    )
    wrappers_parser.add_argument(
        "--dry-run",
        action="store_true",
        help=t('help.install_wrappers.dry_run')
    )
    wrappers_parser.add_argument(
        "--uninstall",
        action="store_true",
        help=t('help.install_wrappers.uninstall')
    )

    args = parser.parse_args()

    # Handle tutorial command (doesn't need WorkflowController)
    if args.command in ("tutorial", "guide"):
        output = run_tutorial(
            list_sections=args.list,
            section=args.section,
            section_name=args.section_name,
            interactive=not (args.list or args.section is not None or args.section_name),
            lang=lang
        )
        if output:
            print(output)
        return

    # Handle init command (doesn't need WorkflowController)
    if args.command == "init":
        if args.list_templates:
            print(show_templates())
        else:
            output = init_project(
                template=args.template,
                project_name=args.name,
                with_claude_md=not args.no_claude_md,
                with_guide=not args.no_guide,
                force=args.force
            )
            print(output)
        return

    # Handle install-wrappers command (doesn't need WorkflowController)
    if args.command == "install-wrappers":
        if args.list:
            print(list_wrappers())
        elif args.uninstall:
            shell = args.shell if args.shell != "auto" else None
            print(uninstall_wrappers(shell=shell))
        else:
            shell = args.shell if args.shell != "auto" else None
            print(install_wrappers(shell=shell, dry_run=args.dry_run))
        return

    try:
        ctrl = WorkflowController(config_path="workflow.yaml")

        if args.command in ("status", "s"):
            print(ctrl.status(track=args.track, all_tracks=args.all_tracks))
        elif args.command == "next":
            print(ctrl.next_stage(args.target, force=args.force, reason=args.reason, token=args.token, skip_conditions=args.skip_conditions, track=args.track))
        elif args.command in ("check", "c"):
            if args.tag:
                # Tag-based check (for shell wrapper automation)
                print(ctrl.check_by_tag(args.tag, evidence=args.evidence, track=args.track))
            elif args.indices:
                # Index-based check
                print(ctrl.check(args.indices, token=args.token, evidence=args.evidence, args=args.args, skip_action=args.skip_action, agent=getattr(args, 'agent', None), track=args.track))
            else:
                print(t('cli.check_error'))
        elif args.command in ("uncheck", "u"):
            print(ctrl.uncheck(args.indices, token=args.token, track=args.track))
        elif args.command == "set":
            print(ctrl.set_stage(args.stage, module=args.module, force=args.force, token=args.token, track=args.track))
        elif args.command == "review":
            print(ctrl.record_review(args.agent, args.summary))
        elif args.command == "secret-generate":
            generate_secret_interactive()
        elif args.command == "install-alias":
            install_alias(args.name)
        elif args.command == "module":
            if args.module_command == "set":
                print(ctrl.set_module(args.name, track=getattr(args, 'track', None)))
            else:
                print(t('cli.module_usage'))
        elif args.command == "track":
            if args.track_command == "create":
                print(ctrl.track_create(args.id, label=args.label, module=args.module, stage=args.stage))
            elif args.track_command == "list":
                print(ctrl.track_list())
            elif args.track_command == "switch":
                print(ctrl.track_switch(args.id))
            elif args.track_command == "join":
                print(ctrl.track_join(force=args.force, token=args.token))
            elif args.track_command == "delete":
                print(ctrl.track_delete(args.id))
            else:
                print(t('cli.track_usage'))
        elif args.command == "phase":
            if args.phase_command == "add":
                depends_on = [d.strip() for d in args.depends_on.split(",") if d.strip()] if args.depends_on else []
                print(ctrl.phase_add(args.id, label=args.label, module=args.module, depends_on=depends_on))
            elif args.phase_command == "list":
                print(ctrl.phase_list())
            elif args.phase_command == "graph":
                print(ctrl.phase_graph())
            elif args.phase_command == "remove":
                print(ctrl.phase_remove(args.id))
            else:
                print(t('cli.phase_usage'))
        else:
            parser.print_help()

    except FileNotFoundError as e:
        print(f"{t('errors.config_not_found', path='workflow.yaml')}")
        print(f"Error: {e}")


def install_alias(name: str):
    """Installs the alias to shell config."""
    script_path = os.path.abspath(__file__)
    python_exe = sys.executable
    cmd = f'{python_exe} -m workflow'

    alias_line = f'alias {name}=\'{cmd}\''

    home = os.path.expanduser("~")
    configs = [".zshrc", ".bashrc", ".bash_profile"]
    target_config = None

    for cfg in configs:
        path = os.path.join(home, cfg)
        if os.path.exists(path):
            target_config = path
            break

    if not target_config:
        print(t('cli.alias.no_config'))
        print(t('cli.alias.add_manually', line=alias_line))
        return

    # Check if already exists
    with open(target_config, 'r') as f:
        content = f.read()
        if f"alias {name}=" in content:
            print(t('cli.alias.already_exists', name=name, config=target_config))
            return

    with open(target_config, 'a') as f:
        f.write(f"\n# AI Workflow Tool\n{alias_line}\n")

    print(t('cli.alias.success', name=name, config=target_config))
    print(t('cli.alias.activate', config=target_config))


if __name__ == "__main__":
    main()
