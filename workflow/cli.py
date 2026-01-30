import argparse
import sys
import os

from .core.controller import WorkflowController
from .core.auth import generate_secret_interactive
from .i18n import t, set_language
from .i18n.detector import detect_language
from .tutorial import run_tutorial
from .init import init_project, show_templates


def main():
    # Pre-parse for --lang flag to set language before building help text
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--lang", "-l", help="Set display language (en, ko)")
    pre_args, _ = pre_parser.parse_known_args()

    # Detect and set language
    lang = detect_language(cli_lang=pre_args.lang)
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
        help=t('help.status.description')
    )
    status_parser.add_argument(
        "--oneline",
        action="store_true",
        help=t('help.status.oneline')
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

    # Check
    check_parser = subparsers.add_parser(
        "check",
        help=t('help.check.description')
    )
    check_parser.add_argument(
        "indices",
        type=int,
        nargs="+",
        help=t('help.check.indices')
    )
    check_parser.add_argument(
        "--token",
        help=t('help.check.token')
    )
    check_parser.add_argument(
        "--evidence", "-e",
        help=t('help.check.evidence')
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

    try:
        ctrl = WorkflowController(config_path="workflow.yaml")

        if args.command == "status":
            print(ctrl.status())
        elif args.command == "next":
            print(ctrl.next_stage(args.target, force=args.force, reason=args.reason))
        elif args.command == "check":
            print(ctrl.check(args.indices, token=args.token, evidence=args.evidence))
        elif args.command == "set":
            ctrl.state.current_stage = args.stage
            if args.module:
                ctrl.state.active_module = args.module
            ctrl.state.save(ctrl.config.state_file)
            print(ctrl.status())
        elif args.command == "review":
            print(ctrl.record_review(args.agent, args.summary))
        elif args.command == "secret-generate":
            generate_secret_interactive()
        elif args.command == "install-alias":
            install_alias(args.name)
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
        print("Could not find shell config file (.zshrc, .bashrc).")
        print(f"Please add this line manually:\n  {alias_line}")
        return

    # Check if already exists
    with open(target_config, 'r') as f:
        content = f.read()
        if f"alias {name}=" in content:
            print(f"Alias '{name}' already exists in {target_config}")
            return

    with open(target_config, 'a') as f:
        f.write(f"\n# AI Workflow Tool\n{alias_line}\n")

    print(f"Success! Added alias '{name}' to {target_config}")
    print(f"Run this to activate: source {target_config}")


if __name__ == "__main__":
    main()
