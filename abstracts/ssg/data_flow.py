from abstracts import index


class DataFlow(index.Index):
    def __init__(self, ssg_graphs):
        self.ssg_graphs = ssg_graphs

    def get_index(self):
        data_flow = 0
        flows = set()
        for func in self.ssg_graphs:
            for edge in list(self.ssg_graphs[func].edges):
                s = edge[0]
                t = edge[1]
                type = self.ssg_graphs[func].edges[(s, t)]['type']
                if type in {"value_flow"}:
                    if (str(s), str(t)) not in flows:
                        data_flow += 1
                        flows.add((str(s), str(t)))
                elif type in {"control_flow"}:
                    pass
                elif type in {"constraint_flow"}:
                    pass
                else:
                    raise Exception("no such type edge: %s", type)
        return data_flow


def get_index_class(ssg_graphs):
    return DataFlow(ssg_graphs)
