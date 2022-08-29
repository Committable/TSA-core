import json
import os

import networkx as nx

from abstracts.ssg import ssg_abstract
from graph_builder import x_graph


class SsgReporter:

    def __init__(self, output_path):
        self.output_path = output_path
        # one func one cfg_json, but there may be more than on contract for
        # a solidity source file, and more than one function for a contract
        # {'contractName':value}
        self.ssg_json = {}
        self.ssg_graphs = {}
        self.ssg_edge_lists = {}

        self.ssg_abstract = {}

        self.ssg_json_path = ''
        self.ssg_abstract_path = ''
        self.ssg_edge_lists_path = ''

    def set_contract_ssg(self, contract_name, xgraph):
        edge_list = []
        node_map = {}

        graphs = xgraph.graphs
        for key in graphs:
            graph = graphs[key]
            graph_key = contract_name + ':' + key
            self.ssg_json[graph_key] = {'nodes': [], 'edges': []}
            self.ssg_graphs[graph_key] = graph

            i = 0

            pos = nx.drawing.nx_agraph.graphviz_layout(graph,
                                                       prog='dot',
                                                       args='-Grankdir=LR')

            for n in list(graph.nodes):
                if isinstance(n, x_graph.ConstraintNode):
                    graph.nodes[n]['shape'] = 'diamond'
                else:
                    graph.nodes[n]['shape'] = 'ellipse'
                graph.nodes[n]['color'] = 'black'
                graph.nodes[n]['label'] = str(n)
                node_map[str(n)] = str(i)
                # todo: add src position for ssg
                self.ssg_json[graph_key]['nodes'].append({
                    'id': str(n),
                    'name': str(n).split('_', maxsplit=1)[0],
                    'pos': str(pos[n]),
                    'src': ''
                })
                i += 1
            for edge in list(graph.edges):
                e = edge[0]
                x = edge[1]

                if graph.edges[(e, x)]['type'] == 'control_flow':
                    graph.edges[(e, x)]['color'] = 'blue'
                    graph.edges[(e, x)]['style'] = 'dashed'
                elif graph.edges[(e, x)]['type'] == 'value_flow':
                    graph.edges[(e, x)]['color'] = 'black'
                    graph.edges[(e, x)]['style'] = 'solid'
                elif graph.edges[(e, x)]['type'] == 'constraint_flow':
                    graph.edges[(e, x)]['color'] = 'red'
                    graph.edges[(e, x)]['style'] = 'dotted'

                graph.edges[(e, x)]['label'] = ''
                for label in graph.edges[(e, x)]['labels']:
                    if graph.edges[(e, x)]['label']:
                        graph.edges[(e, x)]['label'] = label
                    else:
                        graph.edges[(e, x)]['label'] = graph.edges[
                            (e, x)]['label'] + ' | ' + label

                edge_list.append(node_map[str(e)] + ' ' + node_map[str(x)] +
                                 '\n')
                self.ssg_json[graph_key]['edges'].append({
                    'source': str(e),
                    'target': str(x),
                    'type': graph.edges[(e, x)]['type']
                })
        self.ssg_edge_lists[contract_name] = edge_list

    def dump_ssg_json(self):
        self.ssg_json_path = os.path.join(self.output_path, 'ssg.json')
        with open(self.ssg_json_path, 'w', encoding='utf8') as output_file:
            json.dump(self.ssg_json, output_file)

    def print_ssg_graph(self):
        g = nx.DiGraph()
        for ssg in self.ssg_graphs.values():
            for n in list(ssg.nodes):
                node = ssg.nodes[n]
                g.add_node(n, label=node['label'], color=node['color'])

            for edge in list(ssg.edges):
                s = edge[0]
                t = edge[1]
                g.add_edge(s,
                           t,
                           label=ssg.edges[(s, t)]['label'],
                           color=ssg.edges[(s, t)]['color'])

        g1 = nx.nx_agraph.to_agraph(g)
        g1.graph_attr['rankdir'] = 'LR'
        g1.graph_attr['overlap'] = 'scale'
        g1.graph_attr['splines'] = 'polyline'
        g1.graph_attr['ratio'] = 'fill'
        g1.layout(prog='dot')
        g1.draw(path=self.output_path + os.sep + 'ssg.png', format='png')

    def print_function_ssg_graph(self):
        for func, ssg in self.ssg_graphs.items():
            g = nx.DiGraph()

            for n in list(ssg.nodes):
                node = ssg.nodes[n]
                if not g.has_node(node):
                    g.add_node(n,
                               label=node['label'],
                               color=node['color'],
                               shape=node['shape'])

            for edge in list(ssg.edges):
                s = edge[0]
                t = edge[1]
                if not g.has_edge(s, t):
                    g.add_edge(
                        s,
                        t,
                        # TODO(Chao): Should remove or leave as is?
                        # label=self.ssg_graphs[contract][func].edges[(s, t)]['label'],  # pylint: disable=line-too-long
                        label=ssg.edges[(s, t)]['label'],
                        style=ssg.edges[(s, t)]['style'],
                        color=ssg.edges[(s, t)]['color'],
                    )

            g1 = nx.nx_agraph.to_agraph(g)
            g1.graph_attr['rankdir'] = 'LR'
            g1.graph_attr['overlap'] = 'scale'
            g1.graph_attr['splines'] = 'polyline'
            g1.graph_attr['ratio'] = 'fill'
            g1.layout(prog='dot')
            g1.draw(path=os.path.join(self.output_path, func + '_ssg.png'),
                    format='png')

    def dump_ssg_edge_list(self):
        complete = []
        for edge_list in self.ssg_edge_lists.values():
            for i in edge_list:
                complete.append(i)
        self.ssg_edge_lists_path = self.output_path + os.sep + 'ssg_edgelist'
        with open(self.ssg_edge_lists_path, 'w',
                  encoding='utf8') as output_file:
            output_file.write(''.join(complete))

    def construct_ssg_abstract(self, context):
        ssg_abstract_instance = ssg_abstract.SsgAbstract()
        ssg_abstract_instance.register_ssg_abstracts(context)
        self.ssg_abstract = ssg_abstract_instance.get_ssg_abstract_json(
            self.ssg_graphs)

    def dump_ssg_abstract(self):
        self.ssg_abstract_path = os.path.join(self.output_path,
                                              'ssg_abstract.json')
        with open(self.ssg_abstract_path, 'w', encoding='utf8') as output_file:
            json.dump(self.ssg_abstract, output_file)
