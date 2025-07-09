import tree_sitter_javascript as tsjs
import tree_sitter_python as tspython
from tree_sitter import Language

PYTHON = Language(tspython.language())
JAVASCRIPT = Language(tsjs.language())
