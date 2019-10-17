from graphviz import Digraph
from disassembler.wasmConvention import EDGE_UNCONDITIONAL, EDGE_CONDITIONAL_IF, EDGE_CONDITIONAL_BR, \
    EDGE_FALLTHROUGH

class CFGPrinter:
    def __init__(self, func, name):
        self.func = func
        self.name = name
        self.filename = name
        self.design = {'shape': 'box', 'fontname': 'Courier',
                                 'fontsize': '30.0', 'rank': 'same'}

    def printCFG(self, design=None, color='grey', simplify=False):
        g = Digraph('G', filename=self.filename)
        g.attr(rankdir='TB')
        g.attr(overlap='scale')
        g.attr(splines='polyline')
        g.attr(ratio='fill')

        functions = self.cfg.functions
        # only show functions listed

        with g.subgraph(name=self.name, node_attr=design or self.design) as c:
            c.attr(label=self.name)
            c.attr(color=color)
            c.attr(fontsize='50.0')
            c.attr(overlap='false')
            c.attr(splines='polyline')
            c.attr(ratio='fill')

            # create all the basicblocks (blocks)
            for basicblock in self.func.blocks:
                if simplify:
                    # create node
                    c.node(basicblock.start, label=str(basicblock.start)+"_"+str(basicblock.end), splines='true')
                else:
                    label = basicblock.instructions_details()
                    # the escape sequences "\n", "\l" and "\r"
                    # divide the label into lines, centered,
                    # left-justified, and right-justified, respectively.
                    label = label.replace('\n', '\l')
                    # create node
                    c.node(basicblock.name, label=label)
                if len(basicblock.jump_to) > 0:
                    if basicblock.type == EDGE_UNCONDITIONAL:
                        graph.edge(edge.node_from, edge.node_to, color='blue')
                    elif edge.type == EDGE_CONDITIONAL_TRUE:
                        graph.edge(edge.node_from, edge.node_to, color='green')
                    elif edge.type == EDGE_CONDITIONAL_FALSE:
                        graph.edge(edge.node_from, edge.node_to, color='red')
                    elif edge.type == EDGE_FALLTHROUGH:
                        graph.edge(edge.node_from, edge.node_to, color='cyan')
                    elif edge.type == EDGE_CALL and call:
                        graph.edge(edge.node_from, edge.node_to, color='yellow')
                    else:
                        raise Exception('Edge type unknown')

        edges = self.func.edges
        # only get corresponding edges
        if only_func_name:
            functions_block = [func.basicblocks for func in functions]
            block_name = [b.name for block_l in functions_block for b in block_l]
            edges = [edge for edge in edges if (edge.node_from in block_name or edge.node_to in block_name)]
        # insert edges on the graph
        insert_edges_to_graph(g, edges, call)

        g.render(self.filename, view=view)