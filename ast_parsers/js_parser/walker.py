from ast_parsers.tree_sitter_adapter.tree_sitter_ast_walker import TreeSitterAstWalker


class JsAstWalker(TreeSitterAstWalker):
    def __init__(self, ast_type='jsAST'):
        super(JsAstWalker, self).__init__(ast_type)