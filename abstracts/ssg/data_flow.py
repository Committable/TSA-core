from abstracts import index
from utils import context as ctx


class DataFlow(index.Index):

    def __init__(self, ssg_graphs):
        self.ssg_graphs = ssg_graphs

    def get_index(self, context):
        if context.error_type == ctx.ExecErrorType.SYMBOL_TIMEOUT or context.error_type == ctx.ExecErrorType.SYMBOL_EXEC:
            return 0
        data_flow = 0
        flows = set()
        for func in self.ssg_graphs:
            for edge in list(self.ssg_graphs[func].edges):
                s = edge[0]
                t = edge[1]
                edge_type = self.ssg_graphs[func].edges[(s, t)]['type']
                if edge_type in {'value_flow'}:
                    if (str(s), str(t)) not in flows:
                        data_flow += 1
                        flows.add((str(s), str(t)))
                elif edge_type in {'control_flow'}:
                    pass
                elif edge_type in {'constraint_flow'}:
                    pass
                else:
                    raise NotImplementedError(f'no such type edge: {edge_type}')
        return data_flow


def get_index_class(ssg_graphs):
    return DataFlow(ssg_graphs)
