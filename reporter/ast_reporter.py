import json
import os

import networkx as nx


class AstReporter:

    def __init__(self, source, output_path):
        self.source = source

        self.output_path = output_path

        self.ast_json = {}

        self.ast_graph = nx.DiGraph()

        self.ast_abstract = {}

        self.ast_edge_list = []

        self.ast_json_path = ''
        self.ast_abstract_path = ''
        self.ast_edge_list_path = ''

    def set_ast_json(self, ast):
        self.ast_json = ast
        self.ast_json['source'] = self.source

        self._get_ast_graph(ast, self.ast_graph)

        self._add_ast_edge_list(ast, self.ast_edge_list)

    def set_ast_abstract(self, ast_abstract):
        self.ast_abstract = ast_abstract

    def dump_ast_json(self):
        self.ast_json_path = os.path.join(self.output_path, 'ast.json')
        with open(self.ast_json_path, 'w', encoding='utf8') as output_file:
            json.dump(self.ast_json, output_file)

    def print_ast_graph(self):
        g1 = nx.nx_agraph.to_agraph(self.ast_graph)
        g1.graph_attr['rankdir'] = 'LR'
        g1.graph_attr['overlap'] = 'scale'
        g1.graph_attr['splines'] = 'polyline'
        g1.graph_attr['ratio'] = 'fill'
        g1.layout(prog='dot')

        g1.draw(path=os.path.join(self.output_path, 'ast.png'), format='png')

    def dump_ast_edge_list(self):
        self.ast_edge_list_path = os.path.join(self.output_path, 'ast_edgelist')
        with open(self.ast_edge_list_path, 'w',
                  encoding='utf8') as edgelist_file:
            edgelist_file.write(''.join(self.ast_edge_list))

    def dump_ast_abstract(self):
        self.ast_abstract_path = os.path.join(self.output_path,
                                              'ast_abstract.json')
        with open(self.ast_abstract_path, 'w', encoding='utf8') as output_file:
            json.dump(self.ast_abstract, output_file)

    def _add_ast_edge_list(self, node, edge_list):
        if 'children' in node:
            for child in node['children']:
                edge_list.append(node['id'] + ' ' + child['id'] + '\n')
                self._add_ast_edge_list(child, edge_list)

    def _get_ast_graph(self, current, graph):
        if current:
            if 'id' in current:
                node = current

                graph.add_node(node['id'],
                               label=node['name'],
                               ischanged=node['ischanged'],
                               color='red' if node['ischanged'] else 'black')
                if 'children' in current:
                    for child in current['children']:
                        self._get_ast_graph(child, graph)
                        if node['ischanged'] and child['ischanged']:
                            graph.add_edge(node['id'],
                                           child['id'],
                                           ischanged=True,
                                           color='red')
                        else:
                            graph.add_edge(node['id'],
                                           child['id'],
                                           ischanged=False,
                                           color='black')
