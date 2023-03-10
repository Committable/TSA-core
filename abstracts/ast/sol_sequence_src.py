from abstracts import index
from evm_engine.input_dealer import solidity_ast_walker
from solidity_parser import parser_new as parser


class SequenceSrc(index.Index):
    def __init__(self, ast, ast_type, source):
        self.ast = ast
        self.source = source
        self.ast_type = ast_type
        self.sequence_src = 0

    def get_index(self, context):
        if not self.ast or not self.source:
            return 0

        self.sequence_src = 0

        if self.ast_type == 'legacyAST':
            walker = solidity_ast_walker.AstWalker(ast_type='legacyAST')
            nodes = []
            walker.walk(self.ast, {'name': 'FunctionDefinition'}, nodes)
            self.sequence_src += len(nodes)
            nodes = []
            walker.walk(self.ast, {'name': 'EventDefinition'}, nodes)
            self.sequence_src += len(nodes)
            nodes = []
            walker.walk(self.ast, {'name': 'Block'}, nodes)
            for block in nodes:
                for statement in block['children']:
                    del statement  # Unused, reserve for name hint
                    self.sequence_src += 1
        elif self.ast_type == 'ast':
            walker = solidity_ast_walker.AstWalker(ast_type='ast')
            nodes = []
            walker.walk(self.ast, {'nodeType': 'FunctionDefinition'}, nodes)
            self.sequence_src += len(nodes)
            nodes = []
            walker.walk(self.ast, {'nodeType': 'EventDefinition'}, nodes)
            self.sequence_src += len(nodes)
            nodes = []
            walker.walk(self.ast, {'nodeType': 'Block'}, nodes)
            for node in nodes:
                if 'statements' in node:
                    for statement in node['statements']:
                        del statement  # Unused, reserve for name hint
                        self.sequence_src += 1
        elif self.ast_type == 'antlrAST':
            self.visit_ast(self.ast)
        return self.sequence_src

    def visit_ast(self, node):
        if isinstance(node, parser.Node):
            self.sequence_src += 1
            for x in node:
                if isinstance(node[x], parser.Node):
                    self.visit_ast(node[x])
                elif isinstance(node[x], list):
                    for child in node[x]:
                        if isinstance(child, parser.Node):
                            self.visit_ast(child)


def get_index_class(ast, ast_type, source):
    return SequenceSrc(ast, ast_type, source)
