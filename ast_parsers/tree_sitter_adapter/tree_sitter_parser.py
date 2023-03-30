from tree_sitter import Language, Parser
from ast_parsers.ast_parser_interface import AstParserInterface


class TreeSitterParser(AstParserInterface):
    def __init__(self, language, lib_path):
        language = Language(lib_path, language)
        self.parser = Parser()
        self.parser.set_language(language)

    def parse(self, text, start="sourceUnit"):
        tree = self.parser.parse(bytes(text, "utf8"))
        return tree

    def parse_file(self, input_path, start="sourceUnit"):
        with open(input_path, 'r', encoding="utf-8") as f:
            return self.parse(f.read(), start=start)
