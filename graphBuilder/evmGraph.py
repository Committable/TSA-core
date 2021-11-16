import logging
import traceback
from collections import namedtuple
from numpy import long
import six
from z3 import *
from z3.z3util import *
import zlib, base64
from interpreter.symbolicVarGenerator import *
from utils import *
import interpreter.opcodes as opcodes

from graphBuilder.XGraph import *

two_operand_opcode = ("ADD", "MUL", "SUB", "DIV", "SDIV", "SMOD", "MOD", "EQ",
                      "EXP", "SIGNEXTEND", "LT", "GT", "SLT", "SGT",
                      "AND", "OR", "XOR", "BYTE", "SHA3")

overflow_related = ("ADD", "MUL", "SUB", "EXP")

three_operand_opcode = ("ADDMOD", "MULMOD")

one_operand_opcode = ("ISZERO", "NOT")

pass_opcode = ("ADDRESS", "CALLDATASIZE", "CODESIZE", "RETURNDATASIZE", "GASPRICE",
               "EXTCODESIZE", "PC", "MSIZE", "CREATE",
               "EXTCODECOPY", "POP", "LOG0", "LOG1", "LOG2", "LOG3", "LOG4",
               "RETURN", "CALLDATACOPY", "CODECOPY", "RETURNDATACOPY",
               "JUMP", "ORIGIN")

msg_opcode = ("CALLER", "CALLVALUE")

block_opcode = ("COINBASE", "TIMESTAMP", "NUMBER", "DIFFICULTY", "GASLIMIT", "BLOCKHASH")

mem_opcode = ("MLOAD", "MSTORE")

overflow_opcode = ('ADD', 'MUL', 'EXP')

underflow_opcode = ('SUB')

zeorReturnStatusNode = ReturnStatusNode("0", 0)

e_mapping_overflow_var_expr = {}


# def addExpressionNode(graph, expr, path_id): # is_expr(expr) == True and is_const(expr)==False
#     expr = to_symbolic(expr)
#     e_node = graph.getExprNode(expr)
#     if e_node is None:
#         e_node = ExpressionNode(str(expr), expr)
#
#         graph.addExprNode(expr, e_node)
#         flow_edges = []
#         for var in get_vars(expr):
#             node = graph.getVarNode(var)
#             flow_edges.append((node, e_node))
#         graph.addBranchEdge(flow_edges, "flowEdge", path_id)
#         return e_node
#     else:
#         return e_node


# def addConstrainNode(graph, expr, path_id):
#     e_node = graph.getConstrainNode(expr)
#     if e_node is None:
#         e_node = ConstrainNode(str(expr), expr)
#         graph.addConstrainNode(expr, e_node)
#         flow_edges = []
#         for var in get_vars(to_symbolic(expr)):
#             node = graph.getVarNode(var)
#             flow_edges.append((node, e_node))
#         graph.addBranchEdge(flow_edges, "flowEdge", path_id)
#         return e_node
#     else:
#         return e_node


def getSubstitudeExpr(expr, mapping_overflow_var_expr):
    result = to_symbolic(expr)
    while True:
        flag = False
        l_vars = get_vars(result)
        for var in l_vars:
            if var in mapping_overflow_var_expr:
                flag = True
                result = z3.substitute(result, (var, mapping_overflow_var_expr[var]))
        if not flag:
            break

    return convertResult(result)


# def addAddressNode(graph, expr, path_id):
#     expr = to_symbolic(expr)
#     a_node = graph.getAddressNode(expr)
#     if a_node is None:
#         a_node = AddressNode(str(expr), expr)
#         flow_edges = []
#         for var in get_vars(expr):
#             node = graph.getVarNode(var)
#             flow_edges.append((node, a_node))
#         graph.addAddressNode(expr, a_node)
#         graph.addBranchEdge(flow_edges, "flowEdge", path_id)
#         return a_node
#     else:
#         return a_node

def update_graph_computed(graph, opcode, computed, path_conditions_and_vars, pc, param, path_id):
    flow_edges = []
    control_edges = []
    # get node_first
    node_first = addExpressionNode(graph, param[0], path_id)
    # get node_second
    node_second = addExpressionNode(graph, param[1], path_id)
    # get computedNode
    operand = [node_first, node_second]

    computedNode = ArithNode(opcode, operand, pc, path_conditions_and_vars["path_condition"], computed,
                             [getSubstitudeExpr(param[0], e_mapping_overflow_var_expr),
                                getSubstitudeExpr(param[1], e_mapping_overflow_var_expr)],
                             path_id)
    # complete flow_edges and control_edges
    pushEdgesToNode(operand, computedNode, flow_edges)
    pushEdgesToNode(path_conditions_and_vars["path_condition_node"], computedNode, control_edges)

    graph.addBranchEdge(flow_edges, "flowEdge", path_id)
    graph.addBranchEdge(control_edges, "controlEdge", path_id)


    return computedNode


def update_call(graph, opcode, node_stack, global_state, path_conditions_and_vars, path_id):
    node_outgas = node_stack.pop()
    node_recipient = node_stack.pop()
    node_transfer_amount = node_stack.pop()
    node_start_data_input = node_stack.pop()
    node_size_data_input = node_stack.pop()
    node_start_data_output = node_stack.pop()
    node_size_data_ouput = node_stack.pop()

    node_return_status = node_stack.pop()
    node_return_data = node_stack.pop()

    arguments = [node_outgas, node_recipient, node_transfer_amount, node_start_data_input, node_size_data_input,
                 node_start_data_output, node_size_data_ouput]

    call_node = MessageCallNode(opcode, arguments, global_state["pc"], path_conditions_and_vars["path_condition"], path_id)

    graph.addNode(call_node)

    control_edge_list = []
    flow_edge_list = []
    pushEdgesToNode(arguments, call_node, flow_edge_list)
    pushEdgesToNode(path_conditions_and_vars["path_condition_node"], call_node, control_edge_list)
    pushEdge(call_node, node_return_status, flow_edge_list)
    pushEdge(call_node, node_return_data, flow_edge_list)
    graph.addBranchEdge(flow_edge_list, "flowEdge", path_id)
    graph.addBranchEdge(control_edge_list, "controlEdge", path_id)


def update_delegatecall(graph, opcode, node_stack, global_state, path_conditions_and_vars, path_id):
    node_outgas = node_stack.pop()
    node_recipient = node_stack.pop()
    node_start_data_input = node_stack.pop()
    node_size_data_input = node_stack.pop()
    node_start_data_output = node_stack.pop()
    node_size_data_ouput = node_stack.pop()

    node_return_status = node_stack.pop()
    node_return_data = node_stack.pop()

    arguments = [node_outgas, node_recipient, node_start_data_input, node_size_data_input,
                 node_start_data_output, node_size_data_ouput]

    call_node = MessageCallNode(opcode, arguments, global_state["pc"], path_conditions_and_vars["path_condition"], path_id)

    graph.addNode(call_node)

    control_edge_list = []
    flow_edge_list = []
    pushEdgesToNode(arguments, call_node, flow_edge_list)
    pushEdgesToNode(path_conditions_and_vars["path_condition_node"], call_node, control_edge_list)
    pushEdge(call_node, node_return_status, flow_edge_list)
    pushEdge(call_node, node_return_data, flow_edge_list)
    graph.addBranchEdge(flow_edge_list, "flowEdge", path_id)
    graph.addBranchEdge(control_edge_list, "controlEdge", path_id)


def update_suicide(graph, node_stack, global_state, path_conditions_and_vars, path_id):
    node_amount = node_stack.pop(0)
    node_recipient = node_stack.pop(0)

    arguments = [node_recipient, node_amount]

    suicide_node = MessageCallNode("SUICIDE", arguments, global_state["pc"]-1,
                                   path_conditions_and_vars["path_condition"], global_state["pc"], path_id)

    graph.addNode(suicide_node)

    control_edge_list = []
    flow_edge_list = []
    pushEdgesToNode(arguments, suicide_node, flow_edge_list)
    pushEdgesToNode(path_conditions_and_vars["path_condition_node"], suicide_node, control_edge_list)
    graph.addBranchEdge(flow_edge_list, "flowEdge", path_id)
    graph.addBranchEdge(control_edge_list, "controlEdge", path_id)


def update_graph_terminal(graph, opcode, global_state, path_conditions_and_vars, path_id):
    # instruction_name, arguments, global_pc, constraint, nodeID
    node_revert = TerminalNode(opcode, [], global_state["pc"], path_conditions_and_vars["path_condition"], path_id)
    graph.addNode(node_revert)

    control_edge_list = []
    pushEdgesToNode(path_conditions_and_vars["path_condition_node"], node_revert, control_edge_list)
    graph.addBranchEdge(control_edge_list, "controlEdge", path_id)


def pushEdgesToNode(fromNodeList, toNode, edgelist):
    for fromNode in fromNodeList:
        edgelist.append((fromNode, toNode))


def pushEdge(fromNode, toNode, edgelist):
    edgelist.append((fromNode, toNode))


def pushEdges(nodesList, edgelist):
    for item in nodesList:
        edgelist.append(item)
