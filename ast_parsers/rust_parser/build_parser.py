from ast_parsers.tree_sitter_adapter import build_tree_sitter_parser

build_tree_sitter_parser.build_tree_sitter_library('ast_parsers/rust_parser/vendor/tree-sitter-rust',
                                                   'ast_parsers/rust_parser/build/my-languages.so')
