"""Interactive tutorial system for workflow-tool."""
from pathlib import Path
from typing import List, Optional
import os

from ..i18n import t, get_language


class TutorialSection:
    """Represents a tutorial section."""

    def __init__(self, idx: int, name: str, title_key: str):
        """
        Initialize a tutorial section.

        Args:
            idx: Section index (0-based)
            name: Section file name (without extension)
            title_key: i18n key for section title
        """
        self.idx = idx
        self.name = name
        self.title_key = title_key

    @property
    def title(self) -> str:
        """Get localized title."""
        return t(self.title_key)


class TutorialEngine:
    """Engine for running interactive tutorials."""

    SECTIONS = [
        TutorialSection(0, "00_intro", "tutorial.sections.intro"),
        TutorialSection(1, "01_installation", "tutorial.sections.installation"),
        TutorialSection(2, "02_basic_commands", "tutorial.sections.basic_commands"),
        TutorialSection(3, "03_secrets", "tutorial.sections.secrets"),
        TutorialSection(4, "04_advanced", "tutorial.sections.advanced"),
        TutorialSection(5, "05_best_practices", "tutorial.sections.best_practices"),
    ]

    def __init__(self, lang: Optional[str] = None):
        """
        Initialize the tutorial engine.

        Args:
            lang: Language code (uses current i18n language if not specified)
        """
        self.lang = lang or get_language()
        self.current = 0
        self.content_dir = Path(__file__).parent / "content"

    def get_content_path(self, section_idx: int) -> Path:
        """Get the path to a section's content file."""
        if 0 <= section_idx < len(self.SECTIONS):
            section = self.SECTIONS[section_idx]
            return self.content_dir / self.lang / f"{section.name}.md"
        return Path()

    def get_content(self, section_idx: int) -> str:
        """
        Load content for a section.

        Args:
            section_idx: Section index (0-based)

        Returns:
            Section content as markdown string
        """
        path = self.get_content_path(section_idx)

        if path.exists():
            return path.read_text(encoding='utf-8')

        # Fallback to English if translation not available
        if self.lang != 'en':
            fallback_path = self.content_dir / 'en' / f"{self.SECTIONS[section_idx].name}.md"
            if fallback_path.exists():
                return fallback_path.read_text(encoding='utf-8')

        return t('tutorial.section_not_found', name=str(section_idx))

    def list_sections(self) -> str:
        """
        List all available sections.

        Returns:
            Formatted section list
        """
        lines = [
            f"# {t('tutorial.title')}",
            "",
            f"## {t('tutorial.sections')}",
            ""
        ]

        for section in self.SECTIONS:
            marker = ">" if section.idx == self.current else " "
            lines.append(f"{marker} {section.idx}. {section.name.split('_', 1)[1].replace('_', ' ').title()}")

        lines.append("")
        lines.append(f"Use `flow tutorial --section <num>` to view a section.")

        return "\n".join(lines)

    def show_section(self, section_idx: int) -> str:
        """
        Display a specific section.

        Args:
            section_idx: Section index

        Returns:
            Section content with navigation hints
        """
        if not 0 <= section_idx < len(self.SECTIONS):
            return t('tutorial.section_not_found', name=str(section_idx))

        self.current = section_idx
        content = self.get_content(section_idx)

        # Add navigation footer
        nav_parts = []
        if section_idx > 0:
            nav_parts.append(f"[<< Previous: {section_idx - 1}]")
        if section_idx < len(self.SECTIONS) - 1:
            nav_parts.append(f"[Next: {section_idx + 1} >>]")

        if nav_parts:
            content += f"\n\n---\n{' | '.join(nav_parts)}"

        return content

    def run_interactive(self) -> None:
        """Run the tutorial in interactive mode."""
        while True:
            print("\033[2J\033[H")  # Clear screen
            print(self.show_section(self.current))
            print()
            print(f"{t('tutorial.navigation.prev')} | {t('tutorial.navigation.next')} | {t('tutorial.navigation.menu')} | {t('tutorial.navigation.quit')}")

            try:
                choice = input(t('tutorial.prompt')).strip().lower()
            except (KeyboardInterrupt, EOFError):
                print()
                break

            if choice in ('q', 'quit', '종료'):
                break
            elif choice in ('n', 'next', '다음') and self.current < len(self.SECTIONS) - 1:
                self.current += 1
            elif choice in ('p', 'prev', 'previous', '이전') and self.current > 0:
                self.current -= 1
            elif choice in ('m', 'menu', '메뉴'):
                print("\033[2J\033[H")
                print(self.list_sections())
                try:
                    section_input = input("\nEnter section number: ").strip()
                    if section_input.isdigit():
                        idx = int(section_input)
                        if 0 <= idx < len(self.SECTIONS):
                            self.current = idx
                except (KeyboardInterrupt, EOFError):
                    pass
            elif choice.isdigit():
                idx = int(choice)
                if 0 <= idx < len(self.SECTIONS):
                    self.current = idx

        print(t('tutorial.completed'))


def run_tutorial(
    list_sections: bool = False,
    section: Optional[int] = None,
    section_name: Optional[str] = None,
    interactive: bool = False,
    lang: Optional[str] = None
) -> str:
    """
    Main entry point for tutorial functionality.

    Args:
        list_sections: Show section list
        section: Specific section number to show
        section_name: Section name to show
        interactive: Run in interactive mode
        lang: Language override

    Returns:
        Tutorial output string
    """
    engine = TutorialEngine(lang=lang)

    if list_sections:
        return engine.list_sections()

    if section is not None:
        return engine.show_section(section)

    if section_name:
        # Find section by name
        for s in engine.SECTIONS:
            if section_name.lower() in s.name.lower():
                return engine.show_section(s.idx)
        return t('tutorial.section_not_found', name=section_name)

    if interactive:
        engine.run_interactive()
        return ""

    # Default: show first section
    return engine.show_section(0)
