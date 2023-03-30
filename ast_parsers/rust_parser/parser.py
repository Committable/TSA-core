from ast_parsers.tree_sitter_adapter.tree_sitter_parser import  TreeSitterParser


class RustAstParser(TreeSitterParser):
    def __init__(self):
        super(RustAstParser, self).__init__("rust", 'ast_parsers/rust_parser/build/my-languages.so')