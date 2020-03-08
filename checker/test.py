import networkx as nx
from networkx.utils import pairwise



if __name__ == '__main__':
    a = nx.DiGraph()
    a.add_node(1, count=1)
    a.add_node(2, count=1)
    a.add_node(3, count=1)
    a.add_edge(1, 2, label="1")
    a.add_edge(1, 3, label="1")
    a.add_edge(2, 3, label="1")

    paths = nx.all_simple_paths(a, 1, 3)
    print(list(paths))
    # for path in map(pairwise, paths):
    #     for edge in list(path):
    #         print(edge)
    # for single in list(paths):
    #     print(single)
