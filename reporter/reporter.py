import os
import global_params
import json
import logging

import networkx as nx

from inputDealer.solidityAstWalker import AstWalker

logger = logging.getLogger(__name__)


class Reporter:
    def __init__(self, source):
        self.source = source

        self.ast = None
        self.ast_graph = None
        self.ast_edge_list = []

        self.cfgs = {}  # {"contractName":value}
        self.cfg_graphs = {}
        self.cfg_edge_lists = {}

        self.ssgs = {}  # {"contractName":value}}
        self.ssg_graphs = {}
        self.ssg_edge_lists = {}

        self.new_lines = 0

        self.sequence_src = 0
        self.sequence_bin = 0

        self.selection_src = 0
        self.selection_bin = 0

        self.reputation_src = 0
        self.reputation_bin = 0

        self.data_flow = 0
        self.control_flow = 0

    def set_ast(self, ast):
        ast["source"] = self.source
        self.ast = ast

        graph = nx.DiGraph()
        self._get_ast_graph(ast, graph)
        self.ast_graph = graph

        edge_list = []
        self._add_ast_edge_list(ast, edge_list)
        self.ast_edge_list = edge_list

    def add_cfg(self, contract_name, env):
        # 1. construct cfg graph
        cfg = nx.DiGraph(name=contract_name)

        for key in env.vertices:
            basicblock = env.vertices[key]
            label = str(basicblock.start) + "_" + str(basicblock.end)
            cfg.add_node(contract_name + ":" + str(key),
                         instructions=basicblock.instructions,
                         label=label,
                         type=basicblock.get_block_type(),
                         changed=basicblock.changed,
                         src=basicblock.position,
                         lines=basicblock.lines,
                         color="red" if basicblock.changed else "black")
        for key in env.edges:
            for target in env.edges[key]:
                edge_type = env.jump_type[target]
                color = "black"
                if edge_type == "falls_to":
                    color = 'black'
                elif edge_type == "unconditional":
                    color = 'blue'
                elif edge_type == "conditional":
                    color = 'green'
                elif edge_type == "terminal":
                    color = 'red'
                cfg.add_edge(contract_name + ":" + str(key), contract_name + ":" + str(target),
                             type=env.jump_type[target],
                             color=color)

        cfg_json = {}
        cfg_json["nodes"] = []
        cfg_json["edges"] = []

        pos = nx.drawing.nx_agraph.graphviz_layout(cfg, prog='dot', args='-Grankdir=TB')

        for key in env.vertices:
            basicblock = env.vertices[key]
            label = str(basicblock.start) + "_" + str(basicblock.end)
            cfg_json["nodes"].append({"id":   str(key),
                                      "name": label,
                                      "type": basicblock.get_block_type(),
                                      "pos":  str(pos[contract_name + ":" + str(key)]),
                                      "changed": basicblock.changed,
                                      "src": basicblock.position,
                                      "lines": basicblock.lines,
                                      "instructions": basicblock.instructions
                                      })
        edgelist = []
        for key in env.edges:
            for target in env.edges[key]:
                edgelist.append(str(key) + " " + str(target) + "\n")
                cfg_json["edges"].append({"source": str(key), "target": str(target), "type": env.jump_type[target]})

        self.cfgs[contract_name] = cfg_json
        self.cfg_graphs[contract_name] = cfg
        self.cfg_edge_lists[contract_name] = edgelist

    def add_ssg(self, contract_name, graph):
        edgelist = []
        node_map = {}

        graph_json = {}
        graph_json["nodes"] = []
        graph_json["edges"] = []
        i = 0

        pos = nx.drawing.nx_agraph.graphviz_layout(graph, prog='dot', args='-Grankdir=LR')

        for n in list(graph.nodes):
            graph.nodes[n]["color"] = "black"
            graph.nodes[n]["label"] = str(n)
            node_map[str(n)] = str(i)
            graph_json["nodes"].append({"id": str(n),
                                        "name": str(n).split("_")[0],
                                        "pos": str(pos[n]),
                                        "lines": []})
            i += 1
        for edge in list(graph.edges):
            e = edge[0]
            x = edge[1]

            if graph.edges[(e, x)]["label"] == "control_flow" and graph.edges[(e, x)]["boolFlag"]:
                graph.edges[(e, x)]["color"] = 'green'
            elif graph.edges[(e, x)]["label"] == "control_flow" and not graph.edges[(e, x)]["boolFlag"]:
                graph.edges[(e, x)]["color"] = 'blue'
            elif graph.edges[(e, x)]["label"] == "value_flow":
                graph.edges[(e, x)]["color"] = 'black'
            elif graph.edges[(e, x)]["label"] == "constraint_flow":
                graph.edges[(e, x)]["color"] = 'red'

            edgelist.append(node_map[str(e)] + " " + node_map[str(x)] + "\n")
            graph_json["edges"].append(
                {"source": str(e), "target": str(x), "type": graph.edges[(e, x)]["label"]})

        self.ssgs[contract_name] = graph_json
        self.ssg_graphs[contract_name] = graph
        self.ssg_edge_lists[contract_name] = edgelist

    def add_ssg_new(self, contract_name, graphs):
        edgelist = []
        node_map = {}

        graph_json = {}

        for key in graphs:
            graph = graphs[key]
            graph_key = contract_name + ":" + key
            graph_json[graph_key] = {}
            graph_json[graph_key]["nodes"] = []
            graph_json[graph_key]["edges"] = []

            i = 0

            pos = nx.drawing.nx_agraph.graphviz_layout(graph, prog='dot', args='-Grankdir=LR')

            for n in list(graph.nodes):
                graph.nodes[n]["color"] = "black"
                graph.nodes[n]["label"] = str(n)
                node_map[str(n)] = str(i)
                graph_json[graph_key]["nodes"].append({"id": str(n),
                                                       "name": str(n).split("_")[0],
                                                       "pos": str(pos[n]),
                                                       "lines": n.lines})
                i += 1
            for edge in list(graph.edges):
                e = edge[0]
                x = edge[1]

                if graph.edges[(e, x)]["label"] == "control_flow" and graph.edges[(e, x)]["boolFlag"]:
                    graph.edges[(e, x)]["color"] = 'black'
                    graph.edges[(e, x)]["style"] = 'dashed'
                elif graph.edges[(e, x)]["label"] == "control_flow" and not graph.edges[(e, x)]["boolFlag"]:
                    graph.edges[(e, x)]["color"] = 'black'
                    graph.edges[(e, x)]["style"] = 'dashed'
                elif graph.edges[(e, x)]["label"] == "value_flow":
                    graph.edges[(e, x)]["color"] = 'green'
                    graph.edges[(e, x)]["style"] = 'dotted'
                elif graph.edges[(e, x)]["label"] == "constraint_flow":
                    graph.edges[(e, x)]["color"] = 'red'
                    graph.edges[(e, x)]["style"] = 'dotted'

                edgelist.append(node_map[str(e)] + " " + node_map[str(x)] + "\n")
                graph_json[graph_key]["edges"].append(
                    {"source": str(e), "target": str(x), "type": graph.edges[(e, x)]["label"]})

        self.ssgs = graph_json
        self.ssg_graphs[contract_name] = graphs
        self.ssg_edge_lists[contract_name] = edgelist

    def dump_ast(self):
        with open(os.path.join(global_params.DEST_PATH, "ast.json"), 'w') as outputfile:
            json.dump(self.ast, outputfile)

    def print_ast_graph(self):
        g1 = nx.nx_agraph.to_agraph(self.ast_graph)
        g1.graph_attr["rankdir"] = 'LR'
        g1.graph_attr['overlap'] = 'scale'
        g1.graph_attr['splines'] = 'polyline'
        g1.graph_attr['ratio'] = 'fill'
        g1.layout(prog="dot")

        g1.draw(path=global_params.DEST_PATH+os.sep+"ast.png", format='png')
        # g1.render("ast", format='svg', directory=global_params.DEST_PATH, view=False)
        return

    def dump_ast_edge_list(self):
        with open(global_params.DEST_PATH + os.sep + "ast_edgelist", 'w') as edgelist_file:
            edgelist_file.write("".join(self.ast_edge_list))

    def dump_cfg(self):
        with open(os.path.join(global_params.DEST_PATH, "cfg.json"), 'w') as outputfile:
            json.dump(self.cfgs, outputfile)

    def print_cfg_graph(self):
        g = nx.DiGraph()
        for x in self.cfg_graphs:
            for n in list(self.cfg_graphs[x].nodes):
                node = self.cfg_graphs[x].nodes[n]
                # pos = node["src"].split(":")
                # begin = int(pos[0])
                # end = begin + int(pos[1])
                g.add_node(n, label=node["label"], color=node['color'])
            for edge in list(self.cfg_graphs[x].edges):
                s = edge[0]
                t = edge[1]
                g.add_edge(s, t,
                           label=self.cfg_graphs[x].edges[(s, t)]['type'],
                           color=self.cfg_graphs[x].edges[(s, t)]['color']
                           )

        g1 = nx.nx_agraph.to_agraph(g)
        g1.graph_attr["rankdir"] = 'TB'
        g1.graph_attr['overlap'] = 'scale'
        g1.graph_attr['splines'] = 'polyline'
        g1.graph_attr['ratio'] = 'fill'
        g1.layout(prog="dot")
        g1.draw(path=global_params.DEST_PATH + os.sep + "cfg.png", format='png')
        return

    def dump_cfg_edge_list(self):
        complete = []
        for x in self.cfg_edge_lists:
            for i in self.cfg_edge_lists[x]:
                complete.append(i)

        with open(global_params.DEST_PATH + os.sep + "cfg_edgelist", 'w') as edgelist_file:
            edgelist_file.write("".join(complete))

    def dump_ssg(self):
        with open(os.path.join(global_params.DEST_PATH, "ssg.json"), 'w') as outputfile:
            json.dump(self.ssgs, outputfile)

    def print_ssg_graph(self):
        g = nx.DiGraph()
        for x in self.ssg_graphs:
            for n in list(self.ssg_graphs[x].nodes):
                node = self.ssg_graphs[x].nodes[n]
                g.add_node(n, label=node["label"], color=node['color'])

            for edge in list(self.ssg_graphs[x].edges):
                s = edge[0]
                t = edge[1]
                g.add_edge(s, t,
                           label=self.ssg_graphs[x].edges[(s, t)]['label'],
                           color=self.ssg_graphs[x].edges[(s, t)]['color']
                           )

        g1 = nx.nx_agraph.to_agraph(g)
        g1.graph_attr["rankdir"] = 'LR'
        g1.graph_attr['overlap'] = 'scale'
        g1.graph_attr['splines'] = 'polyline'
        g1.graph_attr['ratio'] = 'fill'
        g1.layout(prog="dot")
        g1.draw(path=global_params.DEST_PATH + os.sep + "ssg.png", format='png')
        return

    def print_ssg_graph_new(self):
        g = nx.DiGraph()
        for contract in self.ssg_graphs:
            for func in self.ssg_graphs[contract]:
                for n in list(self.ssg_graphs[contract][func].nodes):
                    node = self.ssg_graphs[contract][func].nodes[n]
                    if not g.has_node(node):
                        g.add_node(n, label=node["label"], color=node['color'])

                for edge in list(self.ssg_graphs[contract][func].edges):
                    s = edge[0]
                    t = edge[1]
                    if not g.has_edge(s, t):
                        g.add_edge(s, t,
                                   # label=self.ssg_graphs[contract][func].edges[(s, t)]['label'],
                                   label="",
                                   style=self.ssg_graphs[contract][func].edges[(s, t)]['style'],
                                   color=self.ssg_graphs[contract][func].edges[(s, t)]['color'],
                                   )

            g1 = nx.nx_agraph.to_agraph(g)
            g1.graph_attr["rankdir"] = 'LR'
            g1.graph_attr['overlap'] = 'scale'
            g1.graph_attr['splines'] = 'polyline'
            g1.graph_attr['ratio'] = 'fill'
            g1.layout(prog="dot")
            g1.draw(path=global_params.DEST_PATH + os.sep + "ssg.png", format='png')
        return

    def dump_ssg_edge_list(self):
        complete = []
        for x in self.ssg_edge_lists:
            for i in self.ssg_edge_lists[x]:
                complete.append(i)

        with open(global_params.DEST_PATH + os.sep + "ssg_edgelist", 'w') as edgelist_file:
            edgelist_file.write("".join(complete))

    def _add_ast_edge_list(self, node, edge_list):
        if "children" in node:
            for child in node["children"]:
                edge_list.append(node["id"] + " " + child["id"] + "\n")
                self._add_ast_edge_list(child, edge_list)

    def _get_ast_graph(self, current, graph):
        if current:
            if "id" in current:
                node = current

                graph.add_node(node["id"],
                               label=node["name"],
                               ischanged=node["ischanged"],
                               color="red" if node["ischanged"] else "black")
                if "children" in current:
                    for child in current["children"]:
                        self._get_ast_graph(child, graph)
                        if node["ischanged"] and child["ischanged"]:
                            graph.add_edge(node["id"], child["id"], ischanged=True, color="red")
                        else:
                            graph.add_edge(node["id"], child["id"], ischanged=False, color="black")

    def get_structure_src(self, ast, source):
        if not ast or not source:
            return
        content = source.get_content()
        if global_params.AST == "legacyAST":
            walker = AstWalker()
            nodes = []
            walker.walk(ast, {"name": "Block"}, nodes)
            for block in nodes:
                for statement in block["children"]:
                    if statement["name"] == "ExpressionStatement":
                        pos = statement["src"].split(":")
                        if "require" in content[int(pos[0]):int(pos[0])+int(pos[1])]:
                            self.selection_src += 1
                    if statement["name"] == "IfStatement":
                        if "children" in statement:
                            self.selection_src += len(statement["children"]) - 1
                    elif statement["name"] in {"WhileStatement", "DoWhileStatement", "ForStatement"}:
                        self.reputation_src += 1
                    else:
                        self.sequence_src += 1
        elif global_params.AST == "ast":
            walker = AstWalker(ast_type="ast")
            nodes = []
            walker.walk(ast, {"nodeType": "Block"}, nodes)
            for node in nodes:
                if "statements" in node:
                    for statement in node["statements"]:
                        if statement["nodeType"] == "ExpressionStatement":
                            pos = statement["src"].split(":")
                            if "require" in content[int(pos[0]):int(pos[0]) + int(pos[1])]:
                                self.selection_src += 1
                        if statement["nodeType"] == "IfStatement":
                            if "trueBody" in statement and statement["trueBody"]:
                                self.selection_src += 1
                            if "falseBody" in statement and statement["falseBody"]:
                                self.selection_src += 1
                        elif statement["nodeType"] in {"WhileStatement", "DoWhileStatement", "ForStatement"}:
                            self.reputation_src += 1
                        else:
                            self.sequence_src += 1

        return

    def get_structure_bin(self):
        cycles = []
        for x in self.cfg_graphs:
            cycles.extend(nx.simple_cycles(self.cfg_graphs[x]))
        self.reputation_bin = len(cycles)

        for x in self.cfg_graphs:
            for edge in list(self.cfg_graphs[x].edges):
                s = edge[0]
                t = edge[1]
                label = self.cfg_graphs[x].edges[(s, t)]['type']
                if label == "conditional":
                    self.selection_bin += 1
                else:
                    self.sequence_bin += 1

    def get_sementic(self):
        for x in self.ssg_graphs:
            for edge in list(self.ssg_graphs[x].edges):
                s = edge[0]
                t = edge[1]
                label = self.ssg_graphs[x].edges[(s, t)]['label']
                if label in {"value_flow"}:
                    self.data_flow += 1
                elif label in {"control_flow"}:
                    self.control_flow += 1
                elif label in {"constraint_flow"}:
                    pass
                else:
                    raise Exception("no such type edge: %s", label)

    def get_sementic_new(self):
        for contract in self.ssg_graphs:
            for func in self.ssg_graphs[contract]:
                for edge in list(self.ssg_graphs[contract][func].edges):
                    s = edge[0]
                    t = edge[1]
                    label = self.ssg_graphs[contract][func].edges[(s, t)]['label']
                    if label in {"value_flow"}:
                        self.data_flow += 1
                    elif label in {"control_flow"}:
                        self.control_flow += 1
                    elif label in {"constraint_flow"}:
                        pass
                    else:
                        raise Exception("no such type edge: %s", label)

    def _get_recursive_blocks(self, ast, walker, nodes):
        new_nodes = []
        walker.walk(ast, {"name": "Block"}, new_nodes)
        for n in new_nodes:
            nodes.append(n)
            for child in n["children"]:
                self._get_recursive_blocks(child, walker, nodes)

    def _get_recursive_if(self, statement):
        for child in statement["children"]:
            if child["name"] == "Block":
                self.selection_src += 1
            elif child["name"] == "IfStatement":
                self._get_recursive_if(child)

    def dump_meta_commit(self):
        meta_commit = {}
        meta_commit["new_lines"] = self.new_lines

        meta_commit["sequence_src"] = self.sequence_src
        meta_commit["sequence_bin"] = self.sequence_bin

        meta_commit["selection_src"] = self.selection_src
        meta_commit["selection_bin"] = self.selection_bin

        meta_commit["reputation_src"] = self.reputation_src
        meta_commit["reputation_bin"] = self.reputation_bin

        meta_commit["data_flow"] = self.data_flow
        meta_commit["control_flow"] = self.control_flow

        with open(os.path.join(global_params.DEST_PATH, "meta_commit.json"), 'w') as outputfile:
            json.dump(meta_commit, outputfile)

    def print_coverage_info(self, contract_name, env, interpreter):
        cfg = self.cfg_graphs[contract_name]
        # get path number
        path_number = 0
        sink_nodes = [node for node, outdegree in list(cfg.out_degree(cfg.nodes())) if outdegree == 0]
        # source_nodes = [node for node, indegree in list(cfg.in_degree(cfg.nodes())) if indegree == 0]
        source_nodes = [contract_name+":0"]
        paths = []
        for sink in sink_nodes:
            for source in source_nodes:
                for path in nx.all_simple_paths(cfg, source=source, target=sink):
                    tmp_path = []
                    flag = True
                    # for i in range(1, len(path)):
                    #     edge = (int(path[i - 1].split(contract_name+":")[1]), int(path[i].split(contract_name+":")[1]))
                    #     if edge in interpreter.impossible_paths:
                    #         flag = False
                    #         break
                    for i in range(0, len(path)):
                        tmp_path.append(int(path[i].split(contract_name+":")[1]))

                    if flag:
                        new_path = []
                        for x in path:
                            new_path.append(int(x.split(contract_name+":")[1]))
                        paths.append(new_path)
                        path_number += 1

        n_s = []
        logger.info("In network not in symbolic:")
        for x in paths:
            if x not in interpreter.paths:
                n_s.append(x)
                # print(x)

        s_n = []
        logger.info("In symbolic not in network:")
        for x in interpreter.paths:
            if x not in paths:
                s_n.append(x)
                # print(x)

        edge_number = cfg.number_of_edges()

        not_visited_edges = []
        for edge in list(cfg.edges):
            s = int(edge[0].split(contract_name+":")[1])
            t = int(edge[1].split(contract_name+":")[1])
            if (s, t) not in interpreter.total_visited_edges:
                not_visited_edges.append((s, t))

        logger.info("Coverage Info: In networkx not symbolic:" + str(len(n_s)))
        logger.info("Coverage Info: In symbolic not networkx:" + str(len(s_n)))
        logger.info("Coverage Info: Visited path: %s", str(interpreter.total_no_of_paths))
        logger.info("Coverage Info: Total path: %d", path_number)
        logger.info("Coverage Info: Visited edge: %d", len(interpreter.total_visited_edges))
        logger.info("Coverage Info: Total edge: %d", edge_number)
        logger.info("Coverage Info: Visited pc: %d", len(interpreter.total_visited_pc))
        logger.info("Coverage Info: Total pc: %d", len(env.instructions))

        # logger.info("Not visited edges:")
        # for edge in not_visited_edges:
        #     logger.info("   %s", str(edge))

        # g = nx.DiGraph()
        # for x in self.cfg_graphs:
        #     for n in list(self.cfg_graphs[x].nodes):
        #         node = self.cfg_graphs[x].nodes[n]
        #         # pos = node["src"].split(":")
        #         # begin = int(pos[0])
        #         # end = begin + int(pos[1])
        #         g.add_node(n, label=node["label"], color=node['color'])
        #     for edge in list(self.cfg_graphs[x].edges):
        #         s = edge[0]
        #         t = edge[1]
        #         s_n = int(edge[0].split(contract_name+":")[1])
        #         s_t = int(edge[1].split(contract_name + ":")[1])
        #         label = ""
        #         if (s_n, s_t) in interpreter.impossible_paths:
        #             label = "impossible"
        #         if (s_n, s_t) in not_visited_edges:
        #             g.add_edge(s, t,
        #                        label=label + "| not visited",
        #                        color="black"
        #                        )
        #         else:
        #             g.add_edge(s, t,
        #                        label=label,
        #                        color="green"
        #                        )


        # g1 = nx.nx_agraph.to_agraph(g)
        # g1.graph_attr["rankdir"] = 'TB'
        # g1.graph_attr['overlap'] = 'scale'
        # g1.graph_attr['splines'] = 'polyline'
        # g1.graph_attr['ratio'] = 'fill'
        # g1.layout(prog="dot")
        # g1.draw(path=global_params.DEST_PATH + os.sep + contract_name + "_cfg.pdf", format='pdf')
        return