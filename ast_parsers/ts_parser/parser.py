from ast_parsers.tree_sitter_adapter.tree_sitter_parser import TreeSitterParser


class TsAstParser(TreeSitterParser):

    def __init__(self):
        super(TsAstParser,
              self).__init__("typescript",
                             'ast_parsers/ts_parser/build/my-languages.so')
