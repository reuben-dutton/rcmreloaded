'''
Pure RGB <-> hex conversions. No dependencies, so any layer can import these
(db.models and db.schemas both do) without risking an import cycle.
'''

from __future__ import annotations


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return ('#%02x%02x%02x' % rgb).upper()


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        raise ValueError("Hex color must be 6 characters long")
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )
