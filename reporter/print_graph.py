from graphviz import Digraph
import networkx as nx
import pygraphviz
from inputDealer.soliditySourceMap import Source
import global_params
import os
import json


def print_ast_nx_graph(graph, file_name="default", design=None, color='grey'):
    g1 = Digraph('G', filename=file_name)
    g1.attr(rankdir='TB')
    g1.attr(overlap='scale')
    g1.attr(splines='polyline')
    g1.attr(ratio='fill')

    edgelist=[]
    node_map = {}
    i = 0
    with g1.subgraph(name=file_name, node_attr=design) as c:
        c.attr(label=file_name)
        c.attr(color=color)
        c.attr(overlap='false')
        c.attr(splines='polyline')
        c.attr(ratio='fill')

        for n in graph.nodes._nodes:
            if graph.nodes._nodes[n]["ischanged"] == True:
                c.node(str(n), label=graph.nodes._nodes[n]["type"], splines='true', color="red")
            node_map[str(n)] = str(i)
            i += 1

        for e in graph.edges._adjdict:
            for x in graph.edges._adjdict[e]:
                if graph.edges._adjdict[e][x]["ischanged"] == True:
                    c.edge(str(e), str(x), color='red')
                edgelist.append(node_map[str(e)]+" "+node_map[str(x)]+"\n")
            # if len(graph.edges._adjdict[e]) == 0 and "content" in graph.nodes._nodes[e] \
            #         and graph.nodes._nodes[e]["ischanged"] == True:
            #     c.node(str(e)+"text", label=graph.nodes._nodes[e]["content"], splines='True', color="green")
            #     c.edge(str(e), str(e)+"text", color='black')

    with open(global_params.DEST_PATH+os.sep+"ast_edgelist", 'w') as edgelist_file:
        edgelist_file.write("".join(edgelist))

    g1.render(file_name, format='svg', directory=global_params.DEST_PATH, view=False)
    return


def print_cfg_nx_graph(graph, file_name="default", design=None, color='grey'):
    g1 = Digraph('G', filename=file_name)
    g1.attr(rankdir='TB')
    g1.attr(overlap='scale')
    g1.attr(splines='polyline')
    g1.attr(ratio='fill')

    edgelist = []
    node_map = {}
    graph_json = {}
    graph_json["nodes"] = []
    graph_json["edges"] = []
    i = 0
    with g1.subgraph(name=file_name, node_attr=design) as c:
        pos = nx.drawing.nx_agraph.graphviz_layout(graph, prog='dot', args='-Grankdir=TB')

        c.attr(label=file_name)
        c.attr(color=color)
        # c.attr(fontsize='50.0')
        c.attr(overlap='false')
        c.attr(splines='polyline')
        c.attr(ratio='fill')

        for n in graph.nodes._nodes:
            block_type = graph.nodes._nodes[n]["type"]
            if block_type == "falls_to":
                c.node(str(n), label=graph.nodes._nodes[n]["label"], splines='true', color="black")
                graph_json["nodes"].append({"id": str(n),
                                            "name": graph.nodes._nodes[n]["label"],
                                            "type": "falls_to",
                                            "pos": str(pos[n]),
                                            "changed": graph.nodes._nodes[n]["changed"],
                                            "src": graph.nodes._nodes[n]["src"]
                                            })
            elif block_type == "unconditional":
                c.node(str(n), label=graph.nodes._nodes[n]["label"], splines='true', color="blue", pos=str(pos[n]))
                graph_json["nodes"].append({"id": str(n),
                                            "name": graph.nodes._nodes[n]["label"],
                                            "type": "unconditional",
                                            "pos": str(pos[n]),
                                            "changed": graph.nodes._nodes[n]["changed"],
                                            "src": graph.nodes._nodes[n]["src"]
                                            })
            elif block_type == "conditional":
                c.node(str(n), label=graph.nodes._nodes[n]["label"], splines='true', color="green", pos=str(pos[n]))
                graph_json["nodes"].append({"id": str(n),
                                            "name": graph.nodes._nodes[n]["label"],
                                            "type": "conditional",
                                            "pos": str(pos[n]),
                                            "changed": graph.nodes._nodes[n]["changed"],
                                            "src": graph.nodes._nodes[n]["src"]
                                            })
            elif block_type == "terminal":
                c.node(str(n), label=graph.nodes._nodes[n]["label"], splines='true', color="red", pos=str(pos[n]))
                graph_json["nodes"].append({"id": str(n),
                                            "name": graph.nodes._nodes[n]["label"],
                                            "type": "terminal",
                                            "pos": str(pos[n]),
                                            "changed": graph.nodes._nodes[n]["changed"],
                                            "src": graph.nodes._nodes[n]["src"]
                                            })
            node_map[str(n)] = str(i)
            i += 1
        for e in graph.edges._adjdict:
            for x in graph.edges._adjdict[e]:
                edge_type = graph.edges._adjdict[e][x]["type"]
                if edge_type == "falls_to":
                    c.edge(str(e), str(x), color='black')
                elif edge_type == "unconditional":
                    c.edge(str(e), str(x), color='blue')
                elif edge_type == "conditional":
                    c.edge(str(e), str(x), color='green')
                elif edge_type == "terminal":
                    c.edge(str(e), str(x), color='red')
                edgelist.append(node_map[str(e)] + " " + node_map[str(x)] + "\n")
                graph_json["edges"].append({"source":str(e), "target":str(x), "type":edge_type})

    with open(global_params.DEST_PATH+os.sep+"cfg_edgelist", 'w') as edgelist_file:
        edgelist_file.write("".join(edgelist))

    g1.render(file_name, format='svg', directory=global_params.DEST_PATH, view=False)
    with open(os.path.join(global_params.DEST_PATH, file_name + ".json"), 'w') as outputfile:
        json.dump(graph_json, outputfile)
    return


def print_ssg_nx_graph(graph, file_name="default", design=None, color='grey'):
    g1 = Digraph('G', filename=file_name)
    g1.attr(rankdir='LR')
    g1.attr(overlap='true')
    g1.attr(splines='polyline')
    g1.attr(ratio='fill')

    edgelist = []
    node_map = {}
    graph_json = {}
    graph_json["nodes"] = []
    graph_json["edges"] = []
    i = 0
    with g1.subgraph(name=file_name, node_attr=design) as c:
        c.attr(label=file_name)
        c.attr(color=color)
        c.attr(overlap='true')
        c.attr(splines='polyline')
        c.attr(rankdir="LR")
        c.attr(ratio='fill')

        pos = nx.drawing.nx_agraph.graphviz_layout(graph, prog='dot', args='-Grankdir=LR')

        for n in graph.nodes._nodes:
            c.node(str(n), label=str(n).split("_")[0], splines='true', color="black")
            node_map[str(n)] = str(i)
            graph_json["nodes"].append({"id": str(n),
                                        "name": str(n).split("_")[0],
                                        "pos": pos[n]})
            i += 1
        for e in graph.edges._adjdict:
            for x in graph.edges._adjdict[e]:
                if graph.edges._adjdict[e][x]["label"] == "flowEdge_address":
                    c.edge(str(e), str(x), color='green')
                elif graph.edges._adjdict[e][x]["label"] == "flowEdge_value":
                    c.edge(str(e), str(x), color='blue')
                elif graph.edges._adjdict[e][x]["label"] == "flowEdge":
                    c.edge(str(e), str(x), color='black')
                elif graph.edges._adjdict[e][x]["label"] == "constraint":
                    c.edge(str(e), str(x), color='red')

                edgelist.append(node_map[str(e)] + " " + node_map[str(x)] + "\n")
                graph_json["edges"].append({"source":str(e), "target":str(x), "type":graph.edges._adjdict[e][x]["label"]})

    with open(global_params.DEST_PATH+os.sep+"ssg_edgelist", 'w') as edgelist_file:
        edgelist_file.write("".join(edgelist))
    g1.render(file_name, format='svg', directory=global_params.DEST_PATH, view=False)
    with open(os.path.join(global_params.DEST_PATH, file_name + ".json"),'w') as outputfile:
        json.dump(graph_json, outputfile)
    return
