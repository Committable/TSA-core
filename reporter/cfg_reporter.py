import json
import os

import networkx as nx

from abstracts.cfg import cfg_abstract
from utils import log


class CfgReporter:

    def __init__(self, output_path):
        self.output_path = output_path
        # one contract one cfg_json, but there may be more than on contract
        # for a solidity source file, {'contractName':value}
        self.cfg_json = {}
        self.cfg_graphs = {}
        self.cfg_edge_lists = {}

        self.cfg_abstract = {}

        self.coverage = {}
        self.information = {}

        self.cfg_json_path = ''
        self.cfg_edge_lists_path = ''
        self.cfg_abstract_path = ''

    def set_contract_cfg(self, contract_name, env):
        # 1. construct cfg graph
        cfg = nx.DiGraph(name=contract_name)

        for key in env.vertices:
            basic_block = env.vertices[key]

            cfg.add_node(f'{contract_name}:{key}',
                         instructions=basic_block.instructions,
                         start=basic_block.start,
                         end=basic_block.end,
                         type=basic_block.get_block_type(),
                         changed=basic_block.changed,
                         src=basic_block.position,
                         lines=basic_block.lines,
                         jump=basic_block.jump_in_type)
        for key in env.edges:
            for target in env.edges[key]:
                source_type = env.vertices[key].get_block_type()
                target_type = env.vertices[target].get_block_type()
                if target_type == "terminal":
                    edge_type = target_type
                else:
                    edge_type = source_type

                cfg.add_edge(f'{contract_name}:{key}',
                             f'{contract_name}:{target}',
                             type=edge_type,
                             jump=env.vertices[key].jump_in_type)

        c_cfg_json = {'nodes': [], 'edges': []}

        pos = nx.drawing.nx_agraph.graphviz_layout(cfg,
                                                   prog='dot',
                                                   args='-Grankdir=TB')

        for key in env.vertices:
            basic_block = env.vertices[key]
            label = f'{basic_block.start}_{basic_block.end}'
            c_cfg_json['nodes'].append({
                'id': str(key),
                'name': label,
                'type': basic_block.get_block_type(),
                'pos': str(pos[f'{contract_name}:{key}']),
                'changed': basic_block.changed,
                'src': basic_block.position,
                'instructions': basic_block.instructions
            })
        edge_list = []
        for key in env.edges:
            for target in env.edges[key]:
                edge_list.append(f'{key} {target}\n')
                c_cfg_json['edges'].append({
                    'source': str(key),
                    'target': str(target),
                    'type': env.jump_type[target]
                })

        self.cfg_json[contract_name] = c_cfg_json
        self.cfg_graphs[contract_name] = cfg
        self.cfg_edge_lists[contract_name] = edge_list

    def construct_cfg_abstract(self, context):
        cfg_abstract_instance = cfg_abstract.CfgAbstract()
        cfg_abstract_instance.register_cfg_abstracts(context)
        self.cfg_abstract = cfg_abstract_instance.get_cfg_abstract_json(
            self.cfg_graphs, context)

    def dump_cfg_json(self):
        self.cfg_json_path = os.path.join(self.output_path, 'cfg.json')
        with open(self.cfg_json_path, 'w', encoding='utf8') as output_file:
            json.dump(self.cfg_json, output_file)

    def print_contract_cfg_graph(self):
        for x, cfg in self.cfg_graphs.items():
            contract_name = x
            g = nx.DiGraph()
            for n in list(cfg.nodes):
                node = cfg.nodes[n]
                g.add_node(n,
                           label=f'{node["start"]}_{node["end"]}',
                           color='red' if node['changed'] else 'black')
            for e in list(cfg.edges):
                s = e[0]
                t = e[1]

                edge = cfg.edges[e]
                edge_type = edge['type']
                color = 'black'
                if edge_type == 'unconditional':
                    color = 'blue'
                elif edge_type == 'conditional':
                    color = 'green'
                elif edge_type == 'terminal':
                    color = 'red'

                g.add_edge(s, t, label=edge['jump'], color=color)

            g1 = nx.nx_agraph.to_agraph(g)
            g1.graph_attr['rankdir'] = 'TB'
            g1.graph_attr['overlap'] = 'scale'
            g1.graph_attr['splines'] = 'polyline'
            g1.graph_attr['ratio'] = 'fill'
            g1.layout(prog='dot')
            g1.draw(path=os.path.join(self.output_path,
                                      f'{contract_name}_cfg.pdf'),
                    format='pdf')

    def print_cfg_graph(self):
        g = nx.DiGraph()
        for x, cfg in self.cfg_graphs.items():
            del x  # Unused, reserve for name hint
            for n in list(cfg.nodes):
                node = cfg.nodes[n]
                g.add_node(n,
                           label=f'{node["start"]}_{node["end"]}',
                           color='red' if node['changed'] else 'black')
            for e in list(cfg.edges):
                s = e[0]
                t = e[1]

                edge = cfg.edges[e]
                edge_type = edge['type']
                color = 'black'
                if edge_type == 'unconditional':
                    color = 'blue'
                elif edge_type == 'conditional':
                    color = 'green'
                elif edge_type == 'terminal':
                    color = 'red'

                g.add_edge(s, t, label=edge['jump'], color=color)

        g1 = nx.nx_agraph.to_agraph(g)
        g1.graph_attr['rankdir'] = 'TB'
        g1.graph_attr['overlap'] = 'scale'
        g1.graph_attr['splines'] = 'polyline'
        g1.graph_attr['ratio'] = 'fill'
        g1.layout(prog='dot')
        g1.draw(path=os.path.join(self.output_path, 'cfg.png'), format='png')

    def dump_cfg_edge_list(self):
        complete = []
        for edge_list in self.cfg_edge_lists.values():
            for i in edge_list:
                complete.append(i)

        self.cfg_edge_lists_path = os.path.join(self.output_path,
                                                'cfg_edgelist')
        with open(self.cfg_edge_lists_path, 'w',
                  encoding='utf8') as edgelist_file:
            edgelist_file.write(''.join(complete))

    def dump_cfg_abstract(self):
        self.cfg_abstract_path = os.path.join(self.output_path,
                                              'cfg_abstract.json')
        with open(self.cfg_abstract_path, 'w', encoding='utf8') as output_file:
            json.dump(self.cfg_abstract, output_file)

    def set_coverage_info(self, contract_name, env, interpreter):
        cfg = self.cfg_graphs[contract_name]
        edge_number = cfg.number_of_edges()

        # not_visited_edges = []
        # for edge in list(cfg.edges):
        #     s = int(edge[0].split(contract_name+':')[1])
        #     t = int(edge[1].split(contract_name+':')[1])
        #     if (s, t) not in interpreter.total_visited_edges:
        #         not_visited_edges.append((s, t))

        log.mylogger.info('Coverage Info: Visited path: %s',
                          str(interpreter.total_no_of_paths))
        log.mylogger.info('Coverage Info: Visited edge: %d',
                          len(interpreter.total_visited_edges) - 1)
        log.mylogger.info('Coverage Info: Total edge: %d', edge_number)
        log.mylogger.info('Coverage Info: Visited pc: %d',
                          len(interpreter.total_visited_pc))
        log.mylogger.info('Coverage Info: Total pc: %d', len(env.instructions))

        self.coverage[contract_name] = {
            'visited_paths': interpreter.total_no_of_paths,
            # subtract (0,0)
            'visited_edges': len(interpreter.total_visited_edges) - 1,
            'total_edges': edge_number,
            'visited_pcs': len(interpreter.total_visited_pc),
            'total_pcs': len(env.instructions)
        }

        # self.information[contract_name] = {
        #     'impossible_edges': interpreter.impossible_paths,
        #     'not_visited_edges': not_visited_edges
        # }

        # log.mylogger.info('Not visited edges:')
        # for edge in not_visited_edges:
        #     log.mylogger.info('   %s', str(edge))
