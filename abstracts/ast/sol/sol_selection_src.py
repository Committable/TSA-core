from abstracts import index
from evm_engine.input_dealer import solidity_ast_walker
from ast_parsers.solidity_parser import parser_new as parser


class SelectionSrc(index.Index):

    def __init__(self, ast, ast_type, source):
        self.ast = ast
        self.source = source
        self.ast_type = ast_type
        self.selection_src = 0

    def get_index(self, context):
        if not self.ast or not self.source:
            return 0
        content = self.source.get_content()

        self.selection_src = 0

        if self.ast_type == 'legacyAST':
            walker = solidity_ast_walker.AstWalker(ast_type='legacyAST')
            nodes = []
            walker.walk(self.ast, {'name': 'Conditional'}, nodes)
            self.selection_src += len(nodes)
            nodes = []
            walker.walk(self.ast, {'name': 'Block'}, nodes)
            for block in nodes:
                for statement in block['children']:
                    if statement['name'] == 'ExpressionStatement':
                        pos = statement['src'].split(':')
                        if 'require(' in content[max(0,
                                                     int(pos[0]) -
                                                     5):int(pos[0]) +
                                                 int(pos[1])]:
                            self.selection_src += 1
                        if 'assert(' in content[max(0,
                                                    int(pos[0]) -
                                                    5):int(pos[0]) +
                                                int(pos[1])]:
                            self.selection_src += 1
                    if statement['name'] == 'IfStatement':
                        if 'children' in statement:
                            self.selection_src += len(statement['children']) - 1
        elif self.ast_type == 'ast':
            walker = solidity_ast_walker.AstWalker(ast_type='ast')
            nodes = []
            walker.walk(self.ast, {'nodeType': 'Conditional'}, nodes)
            self.selection_src += len(nodes)
            nodes = []
            walker.walk(self.ast, {'nodeType': 'Block'}, nodes)
            for node in nodes:
                if 'statements' in node:
                    for statement in node['statements']:
                        if statement['nodeType'] == 'ExpressionStatement':
                            pos = statement['src'].split(':')
                            if 'require(' in content[int(pos[0]):int(pos[0]) +
                                                     int(pos[1])]:
                                self.selection_src += 1
                            if 'assert(' in content[int(pos[0]):int(pos[0]) +
                                                    int(pos[1])]:
                                self.selection_src += 1
                        if statement['nodeType'] == 'IfStatement':
                            if ('trueBody' in statement and
                                    statement['trueBody']):
                                self.selection_src += 1
                            if ('falseBody' in statement and
                                    statement['falseBody']):
                                self.selection_src += 1
        elif self.ast_type == 'antlrAST':
            self.visit_ast(self.ast)
        return self.selection_src

    def visit_ast(self, node):
        if isinstance(node, parser.Node):
            if node['type'] == 'FunctionCall' and 'expression' in node:
                if 'name' in node['expression'] and node['expression']['name'] in ['require', 'assert']:
                    self.selection_src += 1
            if node['type'] == "IfStatement":
                self.selection_src += 1
                if 'FalseBody' in node and node['FalseBody']:
                    self.selection_src += 1
            for x in node:
                if isinstance(node[x], parser.Node):
                    self.visit_ast(node[x])
                elif isinstance(node[x], list):
                    for child in node[x]:
                        if isinstance(child, parser.Node):
                            self.visit_ast(child)


def get_index_class(ast, ast_type, source):
    return SelectionSrc(ast, ast_type, source)
