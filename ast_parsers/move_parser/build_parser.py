from ast_parsers.tree_sitter_adapter import build_tree_sitter_parser

build_tree_sitter_parser.build_tree_sitter_library('ast_parsers/move_parser/vendor/tree-sitter-move',
                                                   'ast_parsers/move_parser/build/my-languages.so')
