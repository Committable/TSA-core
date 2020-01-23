#from graphviz import Digraph
from disassembler.wasmConvention import EDGE_UNCONDITIONAL, EDGE_CONDITIONAL_IF, EDGE_CONDITIONAL_BR, \
    EDGE_FALLTHROUGH

class CFGPrinter:
    def __init__(self, func, name):
        self.func = func
        self.name = name
        self.filename = name
        self.design = {'shape': 'box', 'fontname': 'Courier',
                                 'fontsize': '30.0', 'rank': 'same'}

    def print_CFG(self, design=None, color='grey', simplify=False):
        g = Digraph('G', filename=self.filename)
        g.attr(rankdir='TB')
        g.attr(overlap='scale')
        g.attr(splines='polyline')
        g.attr(ratio='fill')

        # functions = self.cfg.functions
        # only show functions listed

        with g.subgraph(name=self.name, node_attr=design or self.design) as c:
            c.attr(label=self.name)
            c.attr(color=color)
            c.attr(fontsize='50.0')
            c.attr(overlap='false')
            c.attr(splines='polyline')
            c.attr(ratio='fill')

            # create all the basicblocks (blocks)
            for basicblock in self.func.blocks.values():
                if simplify:
                    # create node
                    c.node(str(basicblock.start), label=str(basicblock.start)+"_"+str(basicblock.end), splines='true')
                else:
                    label = basicblock.instructions_details()
                    # the escape sequences "\n", "\l" and "\r"
                    # divide the label into lines, centered,
                    # left-justified, and right-justified, respectively.
                    label = label.replace('\n', '\l')
                    # create node
                    c.node(str(basicblock.start), label=label)
                if len(basicblock.jump_to) > 0:
                    if basicblock.type == EDGE_UNCONDITIONAL:
                        assert(len(basicblock.jump_to) == 1)
                        c.edge(str(basicblock.start), str(basicblock.jump_to[0]), color='blue')
                    elif basicblock.type == EDGE_CONDITIONAL_IF:
                        c.edge(str(basicblock.start), str(basicblock.jump_target), color='green')
                        c.edge(str(basicblock.start), str(basicblock.falls_to), color='red')
                    elif basicblock.type == EDGE_FALLTHROUGH:
                        c.edge(str(basicblock.start), str(basicblock.falls_to), color='cyan')
                    elif basicblock.type == EDGE_CONDITIONAL_BR:
                        for to in basicblock.jump_targets:
                            c.edge(str(basicblock.start), str(to), color='green')
                        c.edge(str(basicblock.start), str(basicblock.falls_to), color='red')
                    else:
                        raise Exception('Edge type unknown')

        g.render(self.filename, view=True)