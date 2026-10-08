from dataclasses import dataclass
from string import Template


@dataclass(frozen=True)
class Prompt:
    """A versioned prompt. Never edit a published version: add a new one (v2) instead,
    so stored results can always be traced to the exact prompt that produced them."""

    name: str
    version: int
    system: str
    template: str

    @property
    def id(self) -> str:
        return f"{self.name}_v{self.version}"

    def render(self, **values: str) -> str:
        """Fill the $placeholders. Raises KeyError if a value is missing."""
        return Template(self.template).substitute(values)
