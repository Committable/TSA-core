from abstracts import index
from evm_engine.input_dealer import solidity_ast_walker
from ast_parsers.solidity_parser import parser_new as parser
from ast_parsers.solidity_parser import antlr_ast_walker as wakler


class TagSolSrc(index.Index):
    def __init__(self, ast, ast_type, source):
        self.ast = ast
        self.source = source
        self.ast_type = ast_type
        self.tag_sol_src = []
        self.walker = wakler.AntlrAstWalker()

    def get_index(self, context):
        if not self.ast or not self.source:
            return []

        if self.ast_type == 'antlrAST':
            self.visit_ast(self.ast)
        return self.tag_sol_src

    def build_call_graph(self, ast):
        call_graphs = {}
        contracts = []
        self.walker.walk(ast, {'type': 'ContractDefinition'}, contracts)
        for contract in contracts:
            call_graph = {}
            call_graphs[contract['name']] = call_graph
            functions = []
            self.walker.walk(contract, {'type': 'FunctionDefinition'}, functions)
            for func in functions:
                callees = []
                caller = Caller(contract['name'], func['name'], func)
                call_graph[caller] = callees

                func_calls = []
                self.walker.walk(func, {'type', 'FunctionCall'}, func_calls)
                for func_call in func_calls:
                    if 'expression' in func_call:
                        callees.append(Callee(func_call['expression']))



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


class Callee:
    def __init__(self, node):
        self.node = node
        self.contract = ''
        self.func = ''
        self._get_name(node)
        self._get_location(node)

    def _get_name(self, node):
        if node['type'] == 'Identifier':
            self.func = node['name']
        elif node['type'] == "MemberAccess":
            if node['expression']['type'] == 'FunctionCall':
                if node['expression']['expression']['type'] == 'Identifier':
                    self.contract = node['expression']['expression']['name']
            self.func = node['memberName']

    def _get_location(self, node):
        self.location = self.node['loc']


class Caller:
    def __init__(self, contract, func, node):
        self.contract = contract
        self.func = func
        self.node = node

    def _get_location(self, node):
        self.location = node['loc']



def get_index_class(ast, ast_type, source):
    return TagSolSrc(ast, ast_type, source)
