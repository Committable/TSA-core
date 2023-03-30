from ast_parsers.tree_sitter_adapter.tree_sitter_ast_walker import TreeSitterAstWalker


class TsAstWalker(TreeSitterAstWalker):
    def __init__(self, ast_type='tsAST', diffs=None):
        if diffs is None:
            diffs = []
        super(TsAstWalker, self).__init__(ast_type, diffs)