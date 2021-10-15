import os
import global_params
import json
import networkx as nx


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
            graph.nodes[n]["label"] = str(n).split("_")[0]
            node_map[str(n)] = str(i)
            graph_json["nodes"].append({"id": str(n),
                                        "name": str(n).split("_")[0],
                                        "pos": str(pos[n]),
                                        "lines": []})
            i += 1
        for edge in list(graph.edges):
            e = edge[0]
            x = edge[1]

            if graph.edges[(e, x)]["label"] == "flowEdge_address":
                graph.edges[(e, x)]["color"] = 'green'
            elif graph.edges[(e, x)]["label"] == "flowEdge_value":
                graph.edges[(e, x)]["color"] = 'blue'
            elif graph.edges[(e, x)]["label"] == "flowEdge":
                graph.edges[(e, x)]["color"] = 'black'
            elif graph.edges[(e, x)]["label"] == "constraint":
                graph.edges[(e, x)]["color"] = 'red'

            edgelist.append(node_map[str(e)] + " " + node_map[str(x)] + "\n")
            graph_json["edges"].append(
                {"source": str(e), "target": str(x), "type": graph.edges[(e, x)]["label"]})

        self.ssgs[contract_name] = graph_json
        self.ssg_graphs[contract_name] = graph
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
        # for x in self.cfg_graphs:
        #     for n in list(self.cfg_graphs[x].nodes):
        #         node = self.cfg_graphs[x].nodes[n]
        #         g.add_node(n, label=node["label"], color=node['color'])
        #     for edge in list(self.cfg_graphs[x].edges):
        #         s = edge[0]
        #         t = edge[1]
        #         g.add_edge(s, t,
        #                    label=self.cfg_graphs[x].edges[(s, t)]['type'],
        #                    color=self.cfg_graphs[x].edges[(s, t)]['color']
        #                    )

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
        # for x in self.ssg_graphs:
        #     for n in list(self.ssg_graphs[x].nodes):
        #         node = self.ssg_graphs[x].nodes[n]
        #         g.add_node(n, label=node["label"], color=node['color'])
        #
        #     for edge in list(self.ssg_graphs[x].edges):
        #         s = edge[0]
        #         t = edge[1]
        #         g.add_edge(s, t,
        #                    label=self.ssg_graphs[x].edges[(s, t)]['label'],
        #                    color=self.ssg_graphs[x].edges[(s, t)]['color']
        #                    )

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
        if "childrent" in node:
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
