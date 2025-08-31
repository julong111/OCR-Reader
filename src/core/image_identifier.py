# src/core/image_identifier.py
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ImageIdentifier:
    # A unique, immutable identifier for an image file, including multi-page context.
    # Replaces the 'path@page' magic string.
    path: str
    page: int = -1  # -1 indicates a single-page image or the file itself

    @classmethod
    def from_string(cls, identifier_str: str) -> ImageIdentifier:
        if '@' in identifier_str:
            path, page_str = identifier_str.rsplit('@', 1)
            try:
                return cls(path=path, page=int(page_str))
            except (ValueError, TypeError):
                # Fallback for invalid format
                return cls(path=identifier_str, page=-1)
        return cls(path=identifier_str, page=-1)

    def __str__(self) -> str:
        # Serializes the identifier back into the 'path@page' string format.
        if self.page > -1:
            return f"{self.path}@{self.page}"
        return self.path

    @property
    def display_name(self) -> str:
        # A user-friendly name for display in UI lists.
        base_name = os.path.basename(self.path)
        if self.page > -1:
            return f"{base_name} - 第 {self.page + 1} 页"
        return base_name
