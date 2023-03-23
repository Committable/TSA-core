from tree_sitter import Language, Parser
from utils import util

# Language.build_library(
#     # Store the library in the `build` directory
#     'js_parser/build/my-languages.so',
#
#     # Include one or more languages
#     [
#         # 'vendor/tree-sitter-go',
#         'js_parser/vendor/tree-sitter-javascript',
#         # 'vendor/tree-sitter-python'
#     ]
# )

# GO_LANGUAGE = Language('build/my-languages.so', 'go')
JS_LANGUAGE = Language('js_parser/build/my-languages.so', 'javascript')
# PY_LANGUAGE = Language('build/my-languages.so', 'python')

parser = Parser()
parser.set_language(JS_LANGUAGE)


def parse(text, start="sourceUnit"):
    tree = parser.parse(bytes(text, "utf8"))
    return tree


def parse_file(path, start="sourceUnit"):
    with open(path, 'r', encoding="utf-8") as f:
        return parse(f.read(), start=start)
