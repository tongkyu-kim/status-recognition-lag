"""Cleaning: map source-specific raw tables onto canonical schemas.

Source layouts are declared in ``config/sources.yaml`` (``reader``, ``column_map``); cleaning code
never guesses them. Outputs go to ``data/interim``.
"""
