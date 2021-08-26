import global_params
from inputDealer.solidityAstWalker import AstWalker


class AstHelper:
    def __init__(self, filename, input_type, sources=None):
        if input_type == global_params.SOLIDITY:
            self.filename = filename
            self.input_type = input_type
            self.source_list = sources[filename]
            self.source = None
        else:
            raise Exception("There is no such type of input")

    def set_source(self, source):
        self.source = source

    def build_ast_graph(self, graph):
        walker = AstWalker(global_params.AST)
        root = self.source_list[global_params.AST]
        return walker.walk_to_graph(self.source, root, graph, 0)
