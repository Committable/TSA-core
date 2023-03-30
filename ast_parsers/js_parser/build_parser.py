from ast_parsers.tree_sitter_adapter import build_tree_sitter_parser

build_tree_sitter_parser.build_tree_sitter_library('ast_parsers/js_parser/vendor/tree-sitter-javascript',
                                                   'ast_parsers/js_parser/build/my-languages.so')
