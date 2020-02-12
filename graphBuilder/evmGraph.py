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

three_operand_opcode = ("ADDMOD", "MULMOD")

one_operand_opcode = ("ISZERO", "NOT")

pass_opcode = ("ADDRESS", "CALLDATASIZE", "CODESIZE", "RETURNDATASIZE", "GASPRICE",
               "EXTCODESIZE", "BLOCKHASH", "PC", "MSIZE", "GAS", "CREATE",
               "EXTCODECOPY", "POP", "LOG0", "LOG1", "LOG2", "LOG3", "LOG4",
               "RETURN", "REVERT", "CALLDATACOPY", "CODECOPY", "RETURNDATACOPY"
               "JUMP")

msg_opcode = ("CALLER", "CALLVALUE")

block_opcode = ("COINBASE", "TIMESTAMP", "NUMBER", "DIFFICULTY", "GASLIMIT")

mem_opcode = ("MLOAD", "MSTORE")


def update_graph_computed(graph, node_stack, opcode, computed, path_conditions_and_vars):
    if opcode in one_operand_opcode:
        node_first = node_stack.pop(0)

        operand = [node_first]
        computedNode = ArithNode(opcode, operand, computed, False)
        edges = [(node_first, computedNode)]
        edgeType = FlowEdge(computedNode)
        graph.addNode(computedNode)
        graph.addEdges(edges, edgeType)
        node_stack.insert(0, computedNode)
    if opcode in two_operand_opcode:
        node_first = node_stack.pop(0)
        node_second = node_stack.pop(0)

        operand = [node_first, node_second]
        computedNode = ArithNode(opcode, operand, computed, False)
        edges = [(node_first, computedNode), (node_second, computedNode)]
        flowEdge = FlowEdge(computedNode)
        graph.addNode(computedNode)
        graph.addEdges(edges, flowEdge)
        # controlEdge = ControlEdge(path_conditions_and_vars["path_condition"])
        # graph.addEdgeList(path_conditions_and_vars["path_condition_node"], computedNode, controlEdge)
        node_stack.insert(0, computedNode)
    elif opcode in three_operand_opcode:
        node_first = node_stack.pop(0)
        node_second = node_stack.pop(0)
        node_third = node_stack.pop(0)

        operand = [node_first, node_second, node_third]
        computedNode = ArithNode(opcode, operand, computed, False)
        edges = [(node_first, computedNode), (node_second, computedNode), (node_third, computedNode)]
        edgeType = FlowEdge(computedNode)
        graph.addNode(computedNode)
        graph.addEdges(edges, edgeType)
        node_stack.insert(0, computedNode)


def update_pass(node_stack, opcode):
    OPCODE = opcodes.opcode_by_name(opcode)
    [node_stack.pop() for _ in range(OPCODE.pop)]
    if OPCODE.push == 1:
        node_stack.insert(0, 0)


def update_graph_msg(graph, node_stack, opcode, value):
    msgNode = MsgDataNode(opcode, value, False)
    graph.addNode(msgNode)
    node_stack.insert(0, msgNode)


def update_graph_block(graph, node_stack, opcode, value, blockNumber):
    node_block = BlockDataNode(opcode, value, blockNumber, False)
    graph.addNode(node_block)
    node_stack.insert(0, node_block)


def update_graph_mload(graph, address, current_miu_i, mem, node_stack, new_var, node_mem):
    node_address = node_stack.pop(0)
    if isAllReal(address, current_miu_i) and address in mem:
        node_value = node_mem[address]
        node_stack.insert(0, node_value)
    else:
        node_stack.insert(0, 0)
        if isReal(address):
            node_mem[address] = new_var
        else:
            node_mem[str(address)] = new_var


def update_graph_mstore(graph, stored_address, stored_value, current_miu_i, node_mem, node_stack):
    node_stored_address = node_stack.pop(0)
    node_stored_value = node_stack.pop(0)
    if isAllReal(stored_address, current_miu_i):
        node_mem[stored_address] = stored_value
    else:
        node_mem[str(stored_address)] = stored_value


def update_graph_sload(graph, path_conditions_and_vars, node_stack, global_state, position, new_var_name, new_var):
    node_position = node_stack.pop(0)
    if isReal(position) and position in global_state["Ia"]:
        pos_node = global_state["pos_to_node"][position]
        node_stack.insert(0, pos_node)
    else:
        if str(position) in global_state["Ia"]:
            pos_node = global_state["pos_to_node"][str(position)]
            node_stack.insert(0, pos_node)
        else:
            node_new_var = StateNode("Ia", new_var_name, new_var, position, False)
            graph.addNode(node_new_var)
            node_stack.insert(0, new_var)
            if isReal(position):
                global_state["pos_to_node"][position] = node_new_var
            else:
                global_state["pos_to_node"][str(position)] = node_new_var
    arguments = [node_position]
    sload_node = InstructionNode("SLOAD", arguments, global_state["pc"], path_conditions_and_vars["path_condition"], False)
    graph.addNode(sload_node)
    controlEdge = ControlEdge(path_conditions_and_vars["path_condition"])
    graph.addEdgeList(path_conditions_and_vars["path_condition_node"], sload_node, controlEdge)


def update_graph_sstore(graph, node_stack, stored_address, global_state, path_conditions_and_vars):
    node_stored_address = node_stack.pop(0)
    node_stored_value = node_stack.pop(0)
    if isReal(stored_address):
        global_state["pos_to_node"][stored_address] = node_stored_value
    else:
        global_state["pos_to_node"][str(stored_address)] = node_stored_value
    arguments = [node_stored_address, node_stored_value]
    sstore_node = InstructionNode("SSTORE", arguments, global_state["pc"], path_conditions_and_vars["path_condition"],
                                  False)
    graph.addNode(sstore_node)
    edges = [(node_stored_value, sstore_node)]
    edgeType = FlowEdge(sstore_node)
    graph.addEdges(edges, edgeType)
    controlEdge = ControlEdge(path_conditions_and_vars["path_condition"])
    graph.addEdgeList(path_conditions_and_vars["path_condition_node"], sstore_node, controlEdge)


def update_jumpi(graph, node_stack, block, flag, node_flag, branch_expression):
    node_target_address = node_stack.pop(0)
    branch_expression_node = ""
    negated_branch_expression_node = ""
    if not isReal(flag):
        compare_node = ConstNode("", 0, False)
        operand = [node_flag, compare_node]

        branch_expression_node = ArithNode("!=", operand, branch_expression, False)
        negated_branch_expression_node = ArithNode("==", operand, Not(branch_expression), False)

        branch_edges = [(node_flag, branch_expression_node), (compare_node, branch_expression_node)]
        negated_branch_edges = [(node_flag, negated_branch_expression_node), (compare_node, negated_branch_expression_node)]
        branch_flowEdge = FlowEdge(branch_expression_node)
        negated_branch_flowEdge = FlowEdge(negated_branch_expression_node)
        graph.addNode(branch_expression_node)
        graph.addEdges(branch_edges, branch_flowEdge)
        graph.addNode(negated_branch_expression_node)
        graph.addEdges(negated_branch_edges, negated_branch_flowEdge)

    block.set_branch_node_experssion(branch_expression_node)
    block.set_negated_branch_node_experssion(negated_branch_expression_node)


def update_graph_const(graph, node_stack, value):
    push_node = ConstNode("", value, False)
    graph.addNode(push_node)
    node_stack.insert(0, push_node)


def update_dup(node_stack, position):
    node_duplicate = node_stack[position]
    node_stack.insert(0, node_duplicate)


def update_swap(node_stack, position):
    node_temp = node_stack[position]
    node_stack[position] = node_stack[0]
    node_stack[0] = node_temp


def update_call(graph, node_stack, global_state, path_conditions_and_vars):
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
    call_node = InstructionNode("CALL", arguments, global_state["pc"], path_conditions_and_vars["path_condition"],
                                False)

    graph.addNode(call_node)


def update_callcode(graph, node_stack, global_state, path_conditions_and_vars ):
    node_transfer_amount = node_stack.pop(0)
    node_start_data_input = node_stack.pop(0)
    node_size_data_input = node_stack.pop(0)
    node_start_data_output = node_stack.pop(0)
    node_size_data_ouput = node_stack.pop(0)

    node_stack.insert(0, 0)

    arguments = [node_transfer_amount, node_start_data_input, node_size_data_input, node_start_data_output,
                 node_size_data_ouput]
    callcode_node = InstructionNode("CALLCODE", arguments, global_state["pc"],
                                    path_conditions_and_vars["path_condition"], False)
    graph.addNode(callcode_node)


def update_delegatecall(graph, node_stack, global_state, path_conditions_and_vars):
    node_stack.pop(0)
    node_recipient = node_stack.pop(0)
    node_stack.pop(0)
    node_stack.pop(0)
    node_stack.pop(0)
    node_stack.pop(0)

    node_stack.insert(0, 0)

    arguments = [node_recipient]
    delegatecall_node = InstructionNode("DELEGATECALL", arguments, global_state["pc"],
                                        path_conditions_and_vars["path_condition"], False)

    graph.addNode(delegatecall_node)


def update_suicide(graph, node_stack, global_state, path_conditions_and_vars):
    node_recipient = node_stack.pop(0)
    arguments = [node_recipient]
    suicide_node = InstructionNode("SUICIDE", arguments, global_state["pc"],
                                   path_conditions_and_vars["path_condition"], False)

    graph.addNode(suicide_node)





