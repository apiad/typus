from .grammar import Grammar

from .backends.gbnf import GBNFCompiler
from .backends.regex import RegexCompiler
from .backends.lark import LarkCompiler


__version__ = "0.3.2"


Grammar.register("gbnf", GBNFCompiler)
Grammar.register("regex", RegexCompiler)
Grammar.register("lark", LarkCompiler)
