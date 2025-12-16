__version__ = "0.0.1"

from .grammar import Grammar
from .backends.gbnf import GBNFCompiler
from .backends.regex import RegexCompiler

# ---------------------------------------------------------
# Default Backend Registration
# ---------------------------------------------------------
# This allows 'g.compile("gbnf")' to work out of the box
# without the Grammar class depending on GBNFCompiler.
Grammar.register("gbnf", GBNFCompiler)
Grammar.register("regex", RegexCompiler)
