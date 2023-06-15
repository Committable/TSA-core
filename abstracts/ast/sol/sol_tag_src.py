import os
from utils import global_params
from abstracts import index
import networkx as nx
from evm_engine.input_dealer import solidity_ast_walker
from ast_parsers.solidity_parser import parser_new as parser
from ast_parsers.solidity_parser import antlr_ast_walker as wakler


class TagSrc(index.Index):
    def __init__(self, ast, ast_type, source):
        self.ast = ast
        self.source = source
        self.ast_type = ast_type
        self.tag_src = set()
        self.walker = wakler.AntlrAstWalker()

    def get_index(self, context):
        if not self.ast or not self.source:
            return []

        if self.ast_type == 'antlrAST':
            call_graphs = self.build_call_graph(self.ast, context)
            # self.print_call_graph(call_graphs)

            if global_params.SKILLS is not None:
                tag_2_lines = {}
                for contract in call_graphs:
                    for caller in call_graphs[contract]:
                        lines = caller.get_lines()
                        for callee in call_graphs[contract][caller]:
                            callee_contract = callee.get_contract()
                            if callee_contract != "":
                                tags = global_params.SKILLS.get_tags_from_contract(callee_contract)
                                for tag in tags:
                                    if tag not in tag_2_lines:
                                        tag_2_lines[tag] = set()
                                    if lines is not None:
                                        tag_2_lines[tag].add(lines)
                # todo with comment lines
                for line in context.get_diff():
                    for tag in tag_2_lines:
                        if tag_2_lines[tag][1] >= line >= tag_2_lines[tag][0]:
                            self.tag_src.add(tag)

        return list(self.tag_src)

    def print_call_graph(self, call_graphs):
        for contract in call_graphs:
            graph = nx.DiGraph()
            for func in call_graphs[contract]:
                graph.add_node(str(func))
                for callee in call_graphs[contract][func]:
                    if graph.has_node(str(callee)):
                        graph.add_node(str(callee))
                    if graph.has_edge(str(func), str(callee)):
                        graph[str(func)][str(callee)]["pos"].append(str(callee.lines))
                    else:
                        graph.add_edge(str(func), str(callee), pos=[str(callee.lines)])
                g1 = nx.nx_agraph.to_agraph(graph)
                g1.graph_attr['rankdir'] = 'LR'
                g1.graph_attr['overlap'] = 'scale'
                g1.graph_attr['splines'] = 'polyline'
                g1.graph_attr['ratio'] = 'fill'
                g1.layout(prog='dot')

                g1.draw(path=os.path.join(global_params.DEST_PATH, contract + '_call_graph.png'), format='png')

    def build_call_graph(self, ast, context):
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
                self.walker.walk(func, {'type': 'FunctionCall'}, func_calls)
                for func_call in func_calls:
                    if 'expression' in func_call:
                        callee = Callee(func_call['expression'])
                        callee.init_name(context)

                        callees.append(callee)
        return call_graphs


class Callee:
    unknown_nounce = 0

    def __init__(self, node):
        self.node = node
        self.contract = ''
        self.func = ''
        self.lines = None
        self._init_lines()

    def init_name(self, context):
        if isinstance(self.node, list):
            for x in self.node:
                if isinstance(x, parser.Node):
                    if context.get_source() is not None:
                        self.func = self.func+context.get_source().get_content_from_position(x['loc']['start']['line'],
                                                                              x['loc']['start']['column'],
                                                                              x['loc']['end']['line'],
                                                                              x['loc']['end']['column'])
                else:
                    self.func = self.func + str(x)
            return
        elif isinstance(self.node, parser.Node):
            if self.node['type'] == 'Identifier':
                self.func = self.node['name']
            elif self.node['type'] == "MemberAccess":
                if self.node['expression']['type'] == 'FunctionCall':
                    if self.node['expression']['expression']['type'] == 'Identifier':
                        self.contract = self.node['expression']['expression']['name']
                if self.node['expression']['type'] == "Identifier":
                    self.contract = self.node['expression']['name']
                self.func = self.node['memberName']
            else:
                self.func = self.func + context.get_source().get_content_from_position(self.node['loc']['start']['line'],
                                                                                       self.node['loc']['start']['column'],
                                                                                       self.node['loc']['end']['line'],
                                                                                       self.node['loc']['end']['column'])
        if self.func == "":
            self.func = "random_"+str(Callee.unknown_nounce)
            Callee.unknown_nounce += 1

    def get_contract(self):
        return self.contract

    def get_func(self):
        return self.func

    def get_lines(self):
        return self.lines

    def _init_lines(self):
        if isinstance(self.node, list):
            for x in self.node:
                if isinstance(x, parser.Node):
                    self.lines = (x['loc']['start']['line'], x['loc']['end']['line'])
                    return
        elif isinstance(self.node, parser.Node):
            self.lines = (self.node['loc']['start']['line'], self.node['loc']['end']['line'])

    def __str__(self):
        if self.contract == '':
            return self.func
        else:
            return self.contract+":"+self.func


class Caller:
    def __init__(self, contract, func, node):
        self.contract = contract
        self.func = func
        self.node = node
        self.lines = None
        self._init_lines()

    def _init_lines(self):
        self.lines = (self.node['loc']['start']['line'], self.node['loc']['end']['line'])

    def get_lines(self):
        return self.lines

    def __str__(self):
        return self.contract+":"+self.func


def get_index_class(ast, ast_type, source):
    return TagSrc(ast, ast_type, source)
