from graphBuilder.XGraph import *
from functools import reduce
from z3 import *
from checker.utils import *
from interpreter import *


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
                branch_id_list.append(graph[path[index]][path[index + 1]]['branchList'])
        if len(list(reduce(lambda x, y: set(x) & set(y), branch_id_list))) > 0:
            return True
    return False


def check_reach_in_special_branch(graph, from_node, to_node, branch_id):
    path_list = get_labeled_paths_between_nodes(graph, "controlEdge", from_node, to_node)
    for path in path_list:
        branch_id_list = []
        for index in range(len(path)):
            if index < len(path) - 1:
                branch_id_list.append(graph[path[index]][path[index + 1]]['branchList'])
            if branch_id in list(reduce(lambda x, y: set(x) & set(y), branch_id_list)):
                return True
    return False


def check_reachable_to_list(graph, from_node, to_node_list):
    path_list = get_labeled_paths_between_nodes(graph, "controlEdge", from_node, to_node_list)
    if len(path_list) > 0:
        return True
    else:
        return False


def get_reachable_to_list(graph, from_node, to_node_list):
    node_reached = []
    for to_node in to_node_list:
        if check_reachable(graph, from_node, to_node):
            node_reached.append(to_node)
    return node_reached


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
    control_node_list = [instruction_node]
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


# 任意一个没有only_owner约束, True表示没有onlyowner约束
def only_owner_check(graph, control_nodes, msg_sender_nodes, state_node_list, sender_node):
    for node in msg_sender_nodes:
        nodes_reached = get_reachable_to_list(graph, node, control_nodes)
        for node_reached in nodes_reached:
            constraint = node_reached.constraint
            # storage_value = state_node.value
            sender_value = sender_node.value
            # 求解成功表示没有约束onlyowner的
            if check_constraint(constraint, sender_value, state_node_list):
                return True
    return False


# def check_caller_taintable(graph, control_nodes, msg_sender_nodes, state_node, sender_node):


def check_storage_taintable(graph, state_node, taint_node_list, msg_sender_nodes, state_node_list, sender_node):
    if check_reachable_from_list(graph, taint_node_list, state_node):

        sstore_nodes = list(graph.predecessors(state_node))
        for sstore_node in sstore_nodes:
            if check_reachable_from_list(graph, taint_node_list, sstore_node):
                control_nodes = get_control_node(graph, sstore_node)
                if not only_owner_check(graph, control_nodes, msg_sender_nodes, state_node_list, sender_node):
                    return True
    return False


def get_taint_sstore_list(graph, state_node, taint_node_list, msg_sender_nodes, sender_node, state_node_list):
    sstore_list = []
    if check_reachable_from_list(graph, taint_node_list, state_node):

        sstore_nodes = list(graph.predecessors(state_node))
        for sstore_node in sstore_nodes:
            if check_reachable_from_list(graph, taint_node_list, sstore_node):
                control_nodes = get_control_node(graph, sstore_node)
                if not only_owner_check(graph, control_nodes, msg_sender_nodes, state_node_list, sender_node):
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


def check_constraint(constraint, sender_value, state_node_list):
    if str(constraint).find('Extract(159, 0, Is') >= 0:
        list_storage = get_vars(constraint)
        pos = ""
        storage_value = ""
        for storage in list_storage:
            if is_storage_var(storage):
                pos = get_storage_position(storage)
        if str(pos) != "":
            for state_node in state_node_list:
                if state_node.position == pos:
                    storage_value = state_node.value
        if str(storage_value) != "":
            solver_is = Solver()
            solver_is.set("timeout", 200)
            solver_is.push()
            solver_is.add(constraint)
            solver_is.add(sender_value == storage_value)
            if not (solver_is.check() == unsat):
                solver_is.pop()
                return True
            else:
                solver_is.pop()
    return False

def query_satisfy(node_first, node_second):
    solver = Solver()
    solver.set("timeout", 200)
    solver.push()
    new_first_constraint, new_second_constraint = refine_constrain(node_first.constraint, node_second.constraint)
    solver.add(new_first_constraint)
    solver.add(new_second_constraint)
    if not (check_sat(solver) == unsat):
        solver.pop()
        return True
    solver.pop()
    return False


def query_satisfy_add_expr(first_node, expression):
    solver_check = Solver()
    solver_check.set("timeout", 200)
    solver_check.push()
    for constraint in first_node.constraint:
        solver_check.add(constraint)
    solver_check.add(expression)
    if not (solver_check.check() == unsat):
        solver_check.pop()
        return True
    solver_check.pop()
    return False


# def remove_condition(constraint):
#     reCondition = []
#     for item in constraint:
#         if str(item).find("Extract(255, 224") >= 0 or str(item).find("Extract(255,224") >= 0:
#             reCondition = constraint[constraint.index(item) + 1:]
#     return reCondition


def refine_constrain(first_constraint, second_constraint):
    new_first_constraint = []
    new_second_constraint =[]
    for condition in first_constraint:
        all_vars = get_vars(condition)
        new_condition = change_vars(all_vars, condition, 1)
        new_first_constraint.append(new_condition)
    for condition in second_constraint:
        all_vars = get_vars(condition)
        new_condition = change_vars(all_vars, condition, 2)
        new_second_constraint.append(new_condition)
    return new_first_constraint, new_second_constraint


def change_vars(all_vars, condition, num):
    for var_name in all_vars:
        if is_inputdata_var(var_name) or is_block_var(var_name):
            new_var_name = str(var_name) + "_" + str(num)
            new_var = BitVec(new_var_name, 256)
            condition = z3.substitute(condition, (var_name, new_var))
    return condition
