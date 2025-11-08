from __future__ import annotations

from string import Template
from typing import Dict

from .template_library import TEMPLATES


class TemplateExpander:
    """Expands named templates with provided variables.

    Uses Python's safe Template substitution; missing variables remain as-is.
    """

    def list_templates(self) -> Dict[str, str]:
        return dict(TEMPLATES)

    def expand(self, name: str, variables: Dict[str, str]) -> str:
        src = TEMPLATES.get(name)
        if not src:
            raise KeyError(f"Unknown template: {name}")
        return Template(src).safe_substitute(**variables)

