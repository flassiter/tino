"""
Command category definitions for organizing commands.

Provides enumeration of command categories used for organizing commands
in the command palette and UI.
"""

from enum import Enum


class CommandCategory(Enum):
    """
    Categories for organizing commands.

    Used by command palette and UI to group related commands together.
    """

    FILE = "File"
    EDIT = "Edit"
    FORMAT = "Format"
    NAVIGATION = "Navigation"
    VIEW = "View"
    TOOLS = "Tools"
    HELP = "Help"

    @classmethod
    def get_all_categories(cls) -> list[str]:
        """Get all category names."""
        return [category.value for category in cls]

    @classmethod
    def from_string(cls, category_str: str) -> "CommandCategory":
        """Get category from string name."""
        for category in cls:
            if category.value.lower() == category_str.lower():
                return category
        raise ValueError(f"Unknown command category: {category_str}")

    def get_display_name(self) -> str:
        """Get the display name for this category."""
        return self.value

    def get_sort_order(self) -> int:
        """Get the sort order for this category in UI."""
        order = {
            self.FILE: 1,
            self.EDIT: 2,
            self.FORMAT: 3,
            self.NAVIGATION: 4,
            self.VIEW: 5,
            self.TOOLS: 6,
            self.HELP: 7,
        }
        return order.get(self, 99)  # type: ignore[no-any-return,call-overload]
