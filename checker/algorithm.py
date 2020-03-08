from graphBuilder.XGraph import *
from functools import reduce
from z3 import *


def check_path_label(graph, path, label):
    for index in range(len(path)):
        if index < len(path) - 1 and graph[path[index]][path[index + 1]]['label'] == 'controlEdge':
            return False
    return True


def get_labeled_paths_between_nodes(graph, label, from_node, to_node):
    path_list = []
    return_list = []
    for path in nx.all_simple_paths(graph, source=from_node, target=to_node):
        path_list.append(list(path))

    for path in path_list:
        if check_path_label(graph, path, label):
            return_list.append(path)
    return return_list


def check_reachable(graph, from_node, to_node):
    path_list = get_labeled_paths_between_nodes(graph, "controlEdge", from_node, to_node)
    if len(path_list) > 0:
        return True
    else:
        return False


def check_reach_in_same_branch(graph, from_node, to_node):
    path_list = get_labeled_paths_between_nodes(graph, "controlEdge", from_node, to_node)
    for path in path_list:
        branch_id_list = []
        for index in range(len(path)):
            if index < len(path) - 1:
                branch_id_list.append(graph[path[index]][path[index+1]]['branchList'])
        if len(list(reduce(lambda x, y: set(x) & set(y), branch_id_list))) > 0:
            return True
    return False


def check_reach_in_special_branch(graph, from_node, to_node, branch_id):
    path_list = get_labeled_paths_between_nodes(graph, "controlEdge", from_node, to_node)
    for path in path_list:
        branch_id_list = []
        for index in range(len(path)):
            if index < len(path) - 1:
                branch_id_list.append(graph[path[index]][path[index+1]]['branchList'])
            if branch_id in list(reduce(lambda x, y: set(x) & set(y), branch_id_list)):
                return True
    return False


def check_reachable_to_list(graph, from_node, to_node_list):
    path_list = get_labeled_paths_between_nodes(graph, "controlEdge", from_node, to_node_list)
    if len(path_list) > 0:
        return True
    else:
        return False


def check_reachable_from_list(graph, from_node_list, to_node):
    for from_node in from_node_list:
        if check_reachable(graph, from_node, to_node):
            return True
    return False


def get_reachable_list(graph, from_node_list, to_node):
    from_reached_list = []
    for from_node in from_node_list:
        if check_reachable(graph, from_node, to_node):
            from_reached_list.append(from_node)
    return from_reached_list


def get_reachable_list_in_branch(graph, from_node_list, to_node, branch_list):
    node_list = []
    for branch_id in branch_list:
        for from_node in from_node_list:
            if check_reach_in_special_branch(graph, from_node, to_node, branch_id):
                node_list.append(from_node)
    return node_list


    # root_nodes = find_root(graph, to_node, to_node)
    # ret = [i for i in root_nodes if i in from_node_list]
    # if len(ret) == 0:
    #     return False
    # else:
    #     return True


# def find_root(graph, node, to_node):
#     if node == to_node:
#         node_list = []
#     parent_list = get_argument_or_flow_node(graph, node)
#     if len(parent_list) == 0:
#         return node
#     else:
#         for parent_node in parent_list:
#             node = find_root(graph, parent_node, to_node)
#             node_list.append(node)
#     return node_list


def get_control_node(graph, instruction_node):
    control_node_list = []
    predecessor_nodes = list(graph.predecessors(instruction_node))
    for item in predecessor_nodes:
        if graph[item][instruction_node]['label'] == "controlEdge":
            control_node_list.append(item)
    return control_node_list


def get_argument_or_flow_node(graph, node):
    argument_node_list = []
    predecessor_nodes = graph.predecessors(node)
    for item in predecessor_nodes:
        if graph[item][node]['label'] == "flowEdge":
            argument_node_list.append(item)
    return argument_node_list


def get_edges_in_same_branch(graph, branch_id):
    all_edges = list(graph.edges())
    branch_edges = []
    for edge in all_edges:
        if branch_id in graph[edge[0]][edge[1]]['branchList'] and (graph[edge[0]][edge[1]]['label'] == "flowEdge"):
            branch_edges.append(edge)
    return branch_edges


def get_nodes_in_same_branch(graph, branch_id):
    node_list = []
    edges = get_edges_in_same_branch(graph, branch_id)
    for edge in edges:
        if not edge[0] in node_list:
            node_list.append(edge[0])
        if not edge[1] in node_list:
            node_list.append(edge[1])
    return node_list


def check_state_change(graph, branch_id, call_node):
    nodes_in_branch = get_nodes_in_same_branch(graph, branch_id)
    for node in nodes_in_branch:
        if type(node) == StateOPNode and node.name == "SSTORE" and node.nodeID < call_node.nodeID:
            return True
    return False


def only_owner_check(graph, control_nodes, msg_sender_nodes):
    for node in msg_sender_nodes:
        if check_reachable_to_list(graph, node, control_nodes):
            return True
    return False


def check_storage_taintable(graph, state_node, taint_node_list, msg_sender_nodes):
    if check_reachable_from_list(graph, taint_node_list, state_node):

        sstore_nodes = list(graph.predecessors(state_node))
        for sstore_node in sstore_nodes:
            if check_reachable_from_list(graph, taint_node_list, sstore_node):
                control_nodes = get_control_node(graph, sstore_node)
                if not only_owner_check(graph, control_nodes, msg_sender_nodes):
                    return True
    return False


def get_taint_sstore_list(graph, state_node, taint_node_list, msg_sender_nodes):
    sstore_list = []
    if check_reachable_from_list(graph, taint_node_list, state_node):

        sstore_nodes = list(graph.predecessors(state_node))
        for sstore_node in sstore_nodes:
            if check_reachable_from_list(graph, taint_node_list, sstore_node):
                control_nodes = get_control_node(graph, sstore_node)
                if not only_owner_check(graph, control_nodes, msg_sender_nodes):
                    sstore_list.append(sstore_node)
    return sstore_list


def get_branchID_list(graph, from_nodes, to_node):
    branch_id = []
    for from_node in from_nodes:
        if not graph[from_node][to_node]['branch'] in branch_id:
            branch_id.append(graph[from_node][to_node]['branch'])
    return branch_id


        # control_nodes = get_control_node(graph, sstore_node)
        # for con







#
# def get_all_flowEdge(graph, node):
#
#
#
# def get_all_parentNode(graph, node, label):
#     print("")


