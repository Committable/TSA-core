from ast_parsers.ast_parser_interface import AstParserInterface
from ast_parsers.solidity_parser import parser_new, parser_old


class AntlrAstParser(AstParserInterface):
    # todo: add flag to differ old from new parser so walker and implement logics for both
    def parse(self, text, start="sourceUnit"):
        try:
            tree = parser_new.parse(text, loc=True)
        except Exception as err:  # pylint: disable=broad-except
            tree = parser_old.parse(text, loc=True)
        return tree

    def parse_file(self, input_path, start="sourceUnit"):
        with open(input_path, 'r', encoding="utf-8") as f:
            return self.parse(f.read(), start=start)
