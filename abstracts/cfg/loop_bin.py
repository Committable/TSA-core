from abstracts import index

import networkx as nx


class LoopBin(index.Index):
    def __init__(self, cfg_graphs):
        self.cfg_graphs = cfg_graphs

    def get_index(self):
        cycles = []
        loops = {}
        loop_bin = 0
        for x in self.cfg_graphs:
            cycles.extend(nx.simple_cycles(self.cfg_graphs[x]))
        for cycle in cycles:
            if cycle[0] in loops:
                if cycle[-1] not in loops[cycle[0]]:
                    loop_bin += 1
                    loops[cycle[0]].add(cycle[-1])
            else:
                loop_bin += 1
                loops[cycle[0]] = set()
                loops[cycle[0]].add(cycle[-1])
        return loop_bin


def get_index_class(cfg_graphs):
    return LoopBin(cfg_graphs)