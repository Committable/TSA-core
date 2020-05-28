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

def addExpressionNode(graph, expr, path_id):
    e_node = graph.getExprNode(expr)
    if e_node is None:
        assert(not is_const(expr))  # a no exist expr mustn't be const or variable type
        e_node = ExpressionNode(str(simplify(expr)), expr)
        flow_edges = []
        for var in get_vars(to_symbolic(expr)):
            node = graph.getVarNode(var)
            flow_edges.append((node, e_node))
        graph.addBranchEdge(flow_edges, "flowEdge", path_id)
        return e_node
    else:
        return e_node

def addAddressNode(graph, expr, path_id):
    a_node = graph.getAddressNode(expr)
    if a_node is None:
        a_node = AddressNode(str(simplify(expr)), expr)
        flow_edges = []
        for var in get_vars(to_symbolic(expr)):
            node = graph.getVarNode(var)
            flow_edges.append((node, a_node))
        graph.addNode(a_node)
        graph.addBranchEdge(flow_edges, "flowEdge", path_id)
        return a_node
    else:
        return a_node

def update_graph_computed(graph, opcode, computed, path_conditions_and_vars, pc, param, path_id):
    var_nodes = []
    flow_edges = []
    control_edges = []
    # get node_first
    if is_expr(param[0]):
        node_first = ExpressionNode(param[0])
        graph.addNode()
        for var in get_vars(param[0]):
            node = graph.getVarNode(var)
            var_nodes.append(node)
            flow_edges.append((node, node_first))
    elif isReal(param[0]):
        node_first = graph.getConstNode(param[0])
    else:
        node_first = graph.getVariableNode(param[0])
    var_nodes.append(node_first)
    # get node_second
    if is_expr(param[1]):
        node_second = ExpressionNode(param[1])
        for var in get_vars(param[1]):
            node = graph.getVariableNode(var)
            var_nodes.append(node)
            flow_edges.append((node, node_second))
    elif isReal(param[1]):
        node_second = graph.getConstNode(param[1])
    else:
        node_second = graph.getVariableNode(param[1])
    var_nodes.append(node_second)
    # get computedNode
    operand = [node_first, node_second]

    computedNode = ArithNode(opcode, operand, pc, path_conditions_and_vars["path_condition"],
                             computed, param, path_id)
    # complete flow_edges and control_edges
    pushEdgesToNode(operand, computedNode, flow_edges)
    pushEdgesToNode(path_conditions_and_vars["path_condition_node"], computedNode, control_edges)

    return var_nodes, flow_edges, control_edges, computedNode


def update_call(graph, opcode, node_stack, global_state, path_conditions_and_vars, path_id):
    node_outgas = node_stack.pop(0)
    node_recipient = node_stack.pop(0)
    node_transfer_amount = node_stack.pop(0)
    node_start_data_input = node_stack.pop(0)
    node_size_data_input = node_stack.pop(0)
    node_start_data_output = node_stack.pop(0)
    node_size_data_ouput = node_stack.pop(0)

    node_return_status = node_stack.pop(0)
    node_return_data = node_stack.pop(0)

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
    node_outgas = node_stack.pop(0)
    node_recipient = node_stack.pop(0)
    node_start_data_input = node_stack.pop(0)
    node_size_data_input = node_stack.pop(0)
    node_start_data_output = node_stack.pop(0)
    node_size_data_ouput = node_stack.pop(0)

    node_return_status = node_stack.pop(0)
    node_return_data = node_stack.pop(0)

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
    node_revert = TerminalNode(opcode, [], global_state["pc"], path_conditions_and_vars["path_condition"],
                               global_state["pc"], path_id)
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
