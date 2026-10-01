"""FlashDSA — spaced-repetition DSA flashcards for interview prep."""

from .cli import VERSION, main

__version__ = VERSION
__all__ = ["VERSION", "__version__", "main"]
