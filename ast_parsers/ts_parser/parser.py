from ast_parsers.tree_sitter_adapter.tree_sitter_parser import  TreeSitterParser


class JsAstParser(TreeSitterParser):
    def __init__(self):
        super(JsAstParser, self).__init__("typescript", 'ast_parsers/ts_parser/build/my-languages.so')
