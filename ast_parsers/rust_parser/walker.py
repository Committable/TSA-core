from ast_parsers.tree_sitter_adapter.tree_sitter_ast_walker import TreeSitterAstWalker


class RustAstWalker(TreeSitterAstWalker):
    def __init__(self, ast_type='rustAST'):
        super(RustAstWalker, self).__init__(ast_type)