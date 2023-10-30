from ast_parsers.tree_sitter_adapter.tree_sitter_parser import TreeSitterParser


class JsAstParser(TreeSitterParser):

    def __init__(self):
        super(JsAstParser,
              self).__init__("javascript",
                             'ast_parsers/js_parser/build/my-languages.so')
