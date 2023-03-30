from ast_parsers.tree_sitter_adapter.tree_sitter_parser import TreeSitterParser


class MoveAstParser(TreeSitterParser):
    def __init__(self):
        super(MoveAstParser, self).__init__("move", 'ast_parsers/move_parser/build/my-languages.so')
