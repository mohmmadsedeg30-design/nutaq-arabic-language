"""لغة نُطْق البرمجية العربية."""

from .core import Interpreter, Lexer, NutaqError, Parser, parse, run

__all__ = ["Interpreter", "Lexer", "NutaqError", "Parser", "parse", "run"]
__version__ = "0.4.0"
