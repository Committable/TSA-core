import logging
import traceback
from collections import namedtuple
from numpy import long
import six
from z3 import *
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
               "EXTCODESIZE", "BLOCKHASH", "PC", "MSIZE", "GAS", "CREATE",
               "EXTCODECOPY", "POP", "LOG0", "LOG1", "LOG2", "LOG3", "LOG4",
               "RETURN", "REVERT", "CALLDATACOPY", "CODECOPY", "RETURNDATACOPY",
               "JUMP", "ORIGIN")

msg_opcode = ("CALLER", "CALLVALUE")

block_opcode = ("COINBASE", "TIMESTAMP", "NUMBER", "DIFFICULTY", "GASLIMIT")

mem_opcode = ("MLOAD", "MSTORE")


def update_graph_computed(graph, node_stack, opcode, computed, path_conditions_and_vars, global_state, control_edge_list, flow_edge_list):
    if opcode in one_operand_opcode:
        node_first = node_stack.pop(0)

        operand = [node_first]
        # global_state["nodeID"] += 1
        computedNode = ArithNode(opcode, operand, global_state["pc"], computed, global_state["pc"])
        # edges = [(node_first, computedNode)]
        # edgeType = FlowEdge(computedNode)
        graph.addNode(computedNode)
        # graph.addEdges(edges, edgeType)
        pushEdge(node_first, computedNode, flow_edge_list)
        node_stack.insert(0, computedNode)
    elif opcode in two_operand_opcode:
        node_first = node_stack.pop(0)
        node_second = node_stack.pop(0)

        operand = [node_first, node_second]
        # global_state["nodeID"] += 1
        computedNode = ArithNode(opcode, operand, global_state["pc"], computed, global_state["pc"])
        # edges = [(node_first, computedNode), (node_second, computedNode)]
        # flowEdge = FlowEdge(computedNode)
        graph.addNode(computedNode)
        # graph.addEdges(edges, flowEdge)

        # controlEdge = ControlEdge(path_conditions_and_vars["path_condition"])
        # graph.addEdgeList(path_conditions_and_vars["path_condition_node"], computedNode, controlEdge)
        node_stack.insert(0, computedNode)
    else:
        node_first = node_stack.pop(0)
        node_second = node_stack.pop(0)
        node_third = node_stack.pop(0)

        operand = [node_first, node_second, node_third]
        # global_state["nodeID"] += 1
        computedNode = ArithNode(opcode, operand, global_state["pc"], computed, global_state["pc"])
        edges = [(node_first, computedNode), (node_second, computedNode), (node_third, computedNode)]
        edgeType = FlowEdge(computedNode)
        graph.addNode(computedNode)
        graph.addEdges(edges, edgeType)
        node_stack.insert(0, computedNode)

    pushEdgesToNode(operand, computedNode, flow_edge_list)
    if opcode in overflow_related:
        pushEdgesToNode(path_conditions_and_vars["path_condition_node"], computedNode, control_edge_list)


def update_pass(node_stack, opcode, global_state):
    OPCODE = opcodes.opcode_by_name(opcode)
    [node_stack.pop(0) for _ in range(OPCODE.pop)]
    if OPCODE.push == 1:
        # global_state["nodeID"] += 1
        new_selfDefinedNode = SelfDefinedNode(opcode, 0, global_state["pc"])
        node_stack.insert(0, new_selfDefinedNode)


def update_graph_msg(graph, node_stack, opcode, global_state):
    # global_state["nodeID"] += 1
    if opcode == "CALLER":
        msgNode = MsgDataNode(opcode, global_state["sender_address"], global_state["pc"])
    else:
        msgNode = MsgDataNode(opcode, global_state["sender_address"], global_state["pc"])
    graph.addNode(msgNode)
    node_stack.insert(0, msgNode)


def update_graph_block(graph, node_stack, opcode, value, blockNumber, global_state):
    # global_state["nodeID"] += 1
    node_block = BlockDataNode(opcode, value, blockNumber, global_state["pc"])
    graph.addNode(node_block)
    node_stack.insert(0, node_block)


def update_graph_mload(graph, address, current_miu_i, mem, node_stack, new_var, node_mem, global_state):
    node_address = node_stack.pop(0)
    if isAllReal(address, current_miu_i) and address in mem:
        node_value = node_mem[address]
        node_stack.insert(0, node_value)
    else:
        # global_state["nodeID"] += 1
        temp_new_selfDefinedNode = SelfDefinedNode("MLOAD", new_var, global_state["pc"])
        node_stack.insert(0, temp_new_selfDefinedNode)
        # global_state["nodeID"] += 1
        # new_selfDefinedNode = SelfDefinedNode("MLOAD", c, global_state["pc"])
        if isReal(address):
            node_mem[address] = temp_new_selfDefinedNode
        else:
            node_mem[str(address)] = temp_new_selfDefinedNode


def update_graph_mstore(graph, stored_address, stored_value, current_miu_i, node_mem, node_stack):
    node_stored_address = node_stack.pop(0)
    node_stored_value = node_stack.pop(0)
    if isAllReal(stored_address, current_miu_i):
        node_mem[stored_address] = node_stored_value
    else:
        node_mem[str(stored_address)] = node_stored_value


def update_graph_sload(graph, path_conditions_and_vars, node_stack, global_state, position, new_var_name, new_var, control_edge_list, flow_edge_list):
    node_position = node_stack.pop(0)
    if isReal(position) and position in global_state["pos_to_node"]:
        pos_node = global_state["pos_to_node"][position]
        node_stack.insert(0, pos_node)
    else:
        if str(position) in global_state["pos_to_node"]:
            pos_node = global_state["pos_to_node"][str(position)]
            node_stack.insert(0, pos_node)
        else:
            # global_state["nodeID"] += 1
            node_new_var = StateNode("Ia", new_var_name, new_var, position, global_state["pc"])
            graph.addNode(node_new_var)
            node_stack.insert(0, node_new_var)
            if isReal(position):
                global_state["pos_to_node"][position] = node_new_var
            else:
                global_state["pos_to_node"][str(position)] = node_new_var
    arguments = [node_position]
    # global_state["nodeID"] += 1
    sload_node = StateOPNode("SLOAD", arguments, global_state["pc"], path_conditions_and_vars["path_condition"],
                             global_state["pc"])
    graph.addNode(sload_node)
    # controlEdge = ControlEdge(path_conditions_and_vars["path_condition_node"])
    # graph.addEdgeList(path_conditions_and_vars["path_condition_node"], sload_node, controlEdge)
    pushEdgesToNode(path_conditions_and_vars["path_condition_node"], sload_node, control_edge_list)


def update_graph_sstore(graph, node_stack, stored_address, global_state, path_conditions_and_vars, control_edge_list, flow_edge_list):
    node_stored_address = node_stack.pop(0)
    node_stored_value = node_stack.pop(0)

    if isReal(stored_address):
        if not stored_address in global_state['pos_to_node']:
            # global_state["nodeID"] += 1
            node_new_var = StateNode("Ia", stored_address, node_stored_value, stored_address, global_state["pc"])
            graph.addNode(node_new_var)
            global_state["pos_to_node"][stored_address] = node_new_var
    else:
        if not str(stored_address) in global_state['pos_to_node']:
            # global_state["nodeID"] += 1
            node_new_var = StateNode("Ia", str(stored_address), node_stored_value, str(stored_address),
                                     global_state["pc"])
            graph.addNode(node_new_var)
            global_state["pos_to_node"][str(stored_address)] = node_new_var

    arguments = [node_stored_address, node_stored_value]
    # global_state["nodeID"] += 1
    sstore_node = StateOPNode("SSTORE", arguments, global_state["pc"], path_conditions_and_vars["path_condition"],
                              global_state["pc"])
    graph.addNode(sstore_node)
    edges = [(node_stored_value, sstore_node), (sstore_node, global_state['pos_to_node'][stored_address])]
    # edgeType = FlowEdge(sstore_node)
    # graph.addEdges(edges, edgeType)
    removeEdge(sstore_node, flow_edge_list)
    removeEdge(sstore_node, control_edge_list)
    pushEdges(edges, flow_edge_list)
    pushEdgesToNode(path_conditions_and_vars["path_condition_node"], sstore_node, control_edge_list)
    # controlEdge = ControlEdge(path_conditions_and_vars["path_condition"])
    # graph.addEdgeList(path_conditions_and_vars["path_condition_node"], sstore_node, controlEdge)


def update_jumpi(graph, node_stack, block, flag, branch_expression, global_state, control_edge_list, flow_edge_list):
    node_target_address = node_stack.pop(0)
    node_flag = node_stack.pop(0)
    branch_expression_node = ""
    negated_branch_expression_node = ""
    if not isReal(flag):
        # global_state["nodeID"] += 1
        compare_node = ConstNode("", 0, global_state["nodeID"])
        operand = [node_flag, compare_node]
        # global_state["nodeID"] += 1
        branch_expression_node = ArithNode("!=", operand, 0, branch_expression, global_state["pc"])
        # global_state["nodeID"] += 1
        negated_branch_expression_node = ArithNode("==", operand, 0, Not(branch_expression), global_state["pc"])

        branch_edges = [(node_flag, branch_expression_node), (compare_node, branch_expression_node)]
        negated_branch_edges = [(node_flag, negated_branch_expression_node),
                                (compare_node, negated_branch_expression_node)]
        # branch_flowEdge = FlowEdge(branch_expression_node)
        # negated_branch_flowEdge = FlowEdge(negated_branch_expression_node)
        graph.addNode(compare_node)
        graph.addNode(branch_expression_node)
        # graph.addEdges(branch_edges, branch_flowEdge)
        graph.addNode(negated_branch_expression_node)
        pushEdges(negated_branch_edges, flow_edge_list)
        pushEdges(branch_edges, flow_edge_list)
        # graph.addEdges(negated_branch_edges, negated_branch_flowEdge)

    block.set_branch_node_experssion(branch_expression_node)
    block.set_negated_branch_node_experssion(negated_branch_expression_node)


def update_graph_const(graph, node_stack, value, global_state):
    # global_state["nodeID"] += 1
    push_node = ConstNode("", value, global_state["pc"])
    graph.addNode(push_node)
    node_stack.insert(0, push_node)


def update_dup(node_stack, position):
    node_duplicate = node_stack[position]
    node_stack.insert(0, node_duplicate)


def update_swap(node_stack, position):
    node_temp = node_stack[position]
    node_stack[position] = node_stack[0]
    node_stack[0] = node_temp


def update_call(graph, node_stack, global_state, path_conditions_and_vars, control_edge_list, flow_edge_list):
    node_outgas = node_stack.pop(0)
    node_recipient = node_stack.pop(0)
    node_transfer_amount = node_stack.pop(0)
    node_start_data_input = node_stack.pop(0)
    node_size_data_input = node_stack.pop(0)
    node_start_data_output = node_stack.pop(0)
    node_size_data_ouput = node_stack.pop(0)

    node_stack.insert(0, 0)

    arguments = [node_outgas, node_recipient, node_transfer_amount, node_start_data_input, node_size_data_input,
                 node_start_data_output, node_size_data_ouput]
    # global_state["nodeID"] += 1call
    call_node = MessageCallNode("CALL", arguments, global_state["pc"], path_conditions_and_vars["path_condition"],
                                global_state["pc"])
    # edgeType = FlowEdge(call_node)

    graph.addNode(call_node)
    # graph.addEdgeList(arguments, _node, edgeType)
    # controlEdge = ControlEdge(path_conditions_and_vars["path_condition"])
    # graph.addEdgeList(path_conditions_and_vars["path_condition_node"], call_node, controlEdge)
    pushEdgesToNode(arguments, call_node, flow_edge_list)
    pushEdgesToNode(path_conditions_and_vars["path_condition_node"], call_node, control_edge_list)


def update_callcode(graph, node_stack, global_state, path_conditions_and_vars, control_edge_list, flow_edge_list):
    node_transfer_amount = node_stack.pop(0)
    node_start_data_input = node_stack.pop(0)
    node_size_data_input = node_stack.pop(0)
    node_start_data_output = node_stack.pop(0)
    node_size_data_ouput = node_stack.pop(0)

    node_stack.insert(0, 0)

    arguments = [node_transfer_amount, node_start_data_input, node_size_data_input, node_start_data_output,
                 node_size_data_ouput]
    # global_state["nodeID"] += 1
    callcode_node = MessageCallNode("CALLCODE", arguments, global_state["pc"],
                                    path_conditions_and_vars["path_condition"], global_state["pc"])
    graph.addNode(callcode_node)
    # edgeType = FlowEdge(callcode_node)
    # graph.addEdgeList(arguments, callcode_node, edgeType)
    pushEdgesToNode(arguments, callcode_node, flow_edge_list)
    pushEdgesToNode(path_conditions_and_vars["path_condition_node"], callcode_node, control_edge_list)


def update_delegatecall(graph, node_stack, global_state, path_conditions_and_vars, control_edge_list, flow_edge_list):
    node_stack.pop(0)
    node_recipient = node_stack.pop(0)
    node_stack.pop(0)
    node_stack.pop(0)
    node_stack.pop(0)
    node_stack.pop(0)

    node_stack.insert(0, 0)

    arguments = [node_recipient]
    # global_state["nodeID"] += 1
    delegatecall_node = MessageCallNode("DELEGATECALL", arguments, global_state["pc"],
                                        path_conditions_and_vars["path_condition"], global_state["pc"])

    graph.addNode(delegatecall_node)
    edgeType = FlowEdge(delegatecall_node)
    # graph.addEdgeList(arguments, delegatecall_node, edgeType)

    pushEdgesToNode(arguments, delegatecall_node, flow_edge_list)
    pushEdgesToNode(path_conditions_and_vars["path_condition_node"], delegatecall_node, control_edge_list)


def update_suicide(graph, node_stack, global_state, path_conditions_and_vars, control_edge_list, flow_edge_list):
    node_recipient = node_stack.pop(0)
    arguments = [node_recipient]
    # global_state["nodeID"] += 1
    suicide_node = MessageCallNode("SUICIDE", arguments, global_state["pc"],
                                   path_conditions_and_vars["path_condition"], global_state["pc"])

    graph.addNode(suicide_node)
    # edgeType = FlowEdge(suicide_node)
    # graph.addEdgeList(arguments, suicide_node, edgeType)

    pushEdgesToNode(arguments, suicide_node, flow_edge_list)
    pushEdgesToNode(path_conditions_and_vars["path_condition_node"], suicide_node, control_edge_list)


def update_graph_inputdata(graph, node_stack, new_var, new_var_name, global_state):
    node_position = node_stack.pop(0)
    # global_state["nodeID"] += 1
    node_new_var = InputDataNode(new_var_name, new_var, global_state["pc"])
    graph.addNode(node_new_var)
    node_stack.insert(0, node_new_var)


def update_graph_balance(graph, node_stack, global_state, flow_edge_list):
    node_address = node_stack.pop(0)
    node_balance = SelfDefinedNode("BALANCE", node_address, global_state["pc"])
    graph.addNode(node_balance)
    node_stack.insert(0, node_balance)
    pushEdge(node_address, node_balance, flow_edge_list)



def pushEdgesToNode(fromNodeList, toNode, edgelist):
    for fromNode in fromNodeList:
        edgelist.append((fromNode, toNode))


def pushEdge(fromNode, toNode, edgelist):
    edgelist.append((fromNode, toNode))


def pushEdges(nodesList, edgelist):
    for item in nodesList:
        edgelist.append(item)


def removeEdge(toNode, edgelist):
    for edge in edgelist:
        if toNode == edge[1]:
            del edge

