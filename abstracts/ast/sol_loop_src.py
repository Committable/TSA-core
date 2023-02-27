from abstracts import index
from input_dealer import solidity_ast_walker
from solidity_parser import parser_new as parser


class LoopSrc(index.Index):

    def __init__(self, ast, ast_type, source):
        self.ast = ast
        self.source = source
        self.ast_type = ast_type
        self.repetition_src = 0

    def get_index(self, context):
        if not self.ast or not self.source:
            return 0
        content = self.source.get_content()
        del content  # Unused, reserve for name hint

        self.repetition_src = 0

        if self.ast_type == 'legacyAST':
            walker = solidity_ast_walker.AstWalker(ast_type='legacyAST')
            nodes = []
            walker.walk(self.ast, {'name': 'Block'}, nodes)
            for block in nodes:
                for statement in block['children']:
                    if statement['name'] in {
                            'WhileStatement', 'DoWhileStatement', 'ForStatement'
                    }:
                        self.repetition_src += 1
        elif self.ast_type == 'ast':
            walker = solidity_ast_walker.AstWalker(ast_type='ast')
            nodes = []
            walker.walk(self.ast, {'nodeType': 'Block'}, nodes)
            for node in nodes:
                if 'statements' in node:
                    for statement in node['statements']:
                        if statement['nodeType'] in {
                                'WhileStatement', 'DoWhileStatement',
                                'ForStatement'
                        }:
                            self.repetition_src += 1
        elif self.ast_type == 'antlrAST':
            self.visit_ast(self.ast)
        return self.repetition_src

    def visit_ast(self, node):
        if isinstance(node, parser.Node):
            if node['type'] in ["ForStatement", "WhileStatement", "DoWhileStatement"]:
                self.repetition_src += 1
            for x in node:
                if isinstance(node[x], parser.Node):
                    self.visit_ast(node[x])
                elif isinstance(node[x], list):
                    for child in node[x]:
                        if isinstance(child, parser.Node):
                            self.visit_ast(child)


def get_index_class(ast, ast_type, source):
    return LoopSrc(ast, ast_type, source)
