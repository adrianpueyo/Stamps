"""State container for Stamps global state."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class StampsContext:
    last_created: Optional[str] = None
    menus_loaded: bool = False
    lock_callbacks: bool = False
