from abstracts import index


class SequenceBin(index.Index):
    def __init__(self, cfg_graphs):
        self.cfg_graphs = cfg_graphs

    def get_index(self):
        sequence_bin = 0
        for x in self.cfg_graphs:
            for edge in list(self.cfg_graphs[x].edges):
                s = edge[0]
                t = edge[1]
                label = self.cfg_graphs[x].edges[(s, t)]['type']
                if label != "conditional":
                    sequence_bin += 1

        return sequence_bin


def get_index_class(cfg_graphs):
    return SequenceBin(cfg_graphs)
