from ast_parsers.tree_sitter_adapter import build_tree_sitter_parser

build_tree_sitter_parser.build_tree_sitter_library(
    'ast_parsers/ts_parser/vendor/tree-sitter-typescript/typescript',
    'ast_parsers/ts_parser/build/my-languages.so')
