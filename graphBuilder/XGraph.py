import networkx as nx
import re
import six
from z3 import *
from solver.symbolicVar import *
import global_params
from utils import isReal, convertResult


class Node:

    def __init__(self, name, fromNodes = None, toNodes = None):
        self.name = name
        self.fromeNodes = fromNodes
        self.toNodes = toNodes

    def getFromNodes(self, graph):
        if self.fromeNodes is None:
            self.fromeNodes = list(graph.perdecessors(self))
        return self.fromeNodes

    def getToNodes(self, graph):
        if self.toNodes is None:
            self.toNodes = list(graph.successors(self))
        return self.toNodes

    def __str__(self):
        return "Node_" + self.name


# CallReturnDataNode is different with ReturnDataNode, but it points to a ReturnDataNode
class CallReturnDataNode(Node):
    def __init__(self, name, pc, path_id):
        super().__init__(name)
        self.pc = pc
        self.path_id = path_id

    def getPc(self):
        return self.pc

    def getPathId(self):
        return self.path_id

    def __str__(self):
        return "CallReturnDataNode_" + self.name + "_" + str(self.pc) + "_" + str(self.path_id)




class InstructionNode(Node):

    def __init__(self, instruction_name, arguments, global_pc, constraint):
        super().__init__(instruction_name)
        self.arguments = arguments
        self.global_pc = global_pc
        self.constraint = constraint

    def getConstraints(self):
        return self.constraint

    def getArguments(self):
        return self.arguments

    def __str__(self):
        return "InstructionNode_" + self.name + "_" + str(self.global_pc)


class MessageCallNode(InstructionNode):

    def __init__(self, instruction_name, arguments, global_pc, constraint, path_id):
        super().__init__(instruction_name, arguments, global_pc, constraint)
        self.path_id = path_id

    def __str__(self):
        return "MessageCallNode_" + self.name + "_" + str(self.global_pc) + "_" + str(self.path_id)


class StateOPNode(InstructionNode):

    def __init__(self, instruction_name, arguments, global_pc, constraint, path_id):
        super().__init__(instruction_name, arguments, global_pc, constraint)
        self.path_id = path_id

    def __str__(self):
        return "StateOPNode_" + self.name + "_" + str(self.global_pc) + "_" + str(self.path_id)


class TerminalNode(InstructionNode):

    def __init__(self, instruction_name, arguments, global_pc, constraint, path_id):
        super().__init__(instruction_name, arguments, global_pc, constraint)
        self.path_id = path_id

    def __str__(self):
        return "TerminalNode_" + self.name + "_" + str(self.path_id)

class ArithNode(InstructionNode):

    def __init__(self, operation, operand, global_pc, constraint, expression, param, path_id):
        super().__init__(operation, operand, global_pc, constraint)
        self.expression = expression
        self.params = param
        self.path_id = path_id

    def __str__(self):
        return "ArithNode_" + self.name + "_" + str(self.global_pc) + "_" + str(self.path_id)

class VariableNode(Node):

    def __init__(self, name, value):
        super().__init__(name)
        self.value = value

    def __str__(self):
        return "VariableNode_" + self.name + "_" + str(self.value)


class ExpressionNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return "ExpressionNode_" + self.name


class ConstrainNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return "ConstrainNode_" + self.name


class StateNode(VariableNode):

    def __init__(self, name, value, position):
        super().__init__(name, value)
        self.position = position

    def __str__(self):
        return "StateNode_" + str(self.name) + "_" + str(self.position)


class ConstNode(VariableNode):

    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return "ConstNode_" + self.name


class InputDataNode(VariableNode):

    def __init__(self, name, value, position):
        super().__init__(name, value)
        self.position = position

    def __str__(self):
        return "InputDataNode_" + self.name


class InputDataSizeNode(VariableNode):

    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return "InputDataSizeNode_" + self.name


class ExpNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return "ExpNode_" + self.name


class GasPriceNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return "GasPriceNode_" + self.name


class OriginNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return "OriginNode_" + self.name


class CoinbaseNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return "CoinbaseNode_" + self.name


class DifficultyNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return "DifficultyNode_" + self.name


class GasLimitNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return "GasLimitNode_"  + self.name


class CurrentNumberNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return "CurrentNumberNode_" + self.name


class TimeStampNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return "TimeStampNode_" + self.name


class AddressNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return "AddressNode_" + self.name


class BlockhashNode(VariableNode):
    def __init__(self, name, value, blockNumber):
        super().__init__(name, value)
        self.blockNumber = blockNumber

    def __str__(self):
        return "BlockhashNode_" + self.name + "_" + str(self.blockNumber)


class GasNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return "GasNode_" + self.name


class ShaNode(VariableNode):
    def __init__(self, name, value, args):
        super().__init__(name, value)
        self.args = args

    def __str__(self):
        return "ShaNode_" + str(self.args)


class MemoryNode(VariableNode):

    def __init__(self, name, value, position):
        super().__init__(name, value)
        self.position = position

    def __str__(self):
        return "MemoryNode_" + self.name


class ExtcodeSizeNode(VariableNode):
    def __init__(self, name, value, address):
        super().__init__(name, value)
        self.address = address

    def __str__(self):
        return "ExtcodeSizeNode_" + self.name


class DepositValueNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return "DepositValueNode_" + self.name


class BalanceNode(VariableNode):
    def __init__(self, name, value, address):
        super().__init__(name, value)
        self.address = address

    def __str__(self):
        return "BalanceNode_" + self.name


class ReturnDataNode(VariableNode):

    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return "ReturnDataNode_" + self.name


class ReturnStatusNode(VariableNode):

    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return "ReturnStatusNode_" + self.name


class ReturnDataSizeNode(VariableNode):

    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return "ReturnDataSizeNode_" + self.name


class CodeNode(VariableNode):

    def __init__(self, name, value, address):
        super().__init__(name, value)
        self.address = address

    def __str__(self):
        return "CodeNode_" + self.name


class SenderNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return "SenderNode_" + self.name


class ReceiverNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return "ReceiverNode_" + self.name


class XGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.ssg = nx.DiGraph()
        self.count = 0
        self.overflow_related = ('ADD', 'SUB', 'MUL', 'EXP')

        self.message_call_nodes = []  # all nodes included in {call, staticcall, delegatecall, callcode}
        self.call_nodes = []  # for call instruction
        self.arith_nodes = []  # only for {"add", "sub", "mul", "exp"}
        self.state_op_nodes = []  # all nodes included in {sstore, sload}
        self.sstore_nodes = []  # for sstore instruction
        self.input_data_nodes = []  # for {calldataload, calldatacopy}
        self.state_nodes = []
        self.terminal_nodes = []  # for "revert"
        self.sender_node = None  # for msg.sender
        self.receiver_node = None  # for receiver
        self.deposit_value_node = None # Iv
        self.address_nodes = []  # for all address nodes
        self.return_status_nodes = []  # for all return status nodes


        # (Var, VariableNode), mapping symbolic or real int to variableNodes
        self.mapping_var_node = {}
        # (expr, ExpressionNode)
        self.mapping_expr_node = {}
        # (constrain, ConstrainNode)
        self.mapping_constrain_node = {}
        # (expr/var, AddressNode)
        self.mapping_address_node = {}
        # (pc, [CallReturnNode])
        self.mapping_pc_callReturnNode = {}
        # (position, StateNode)
        self.mapping_position_stateNode = {}

    def addConstrainNode(self, constrain, node):
        self.mapping_constrain_node[constrain] = node

    def getConstrainNode(self, constrain):
        if constrain in self.mapping_constrain_node:
            return self.mapping_constrain_node[constrain]
        else:
            return None

    def addStateNode(self, position, node):
        self.mapping_position_stateNode[position] = node

    def getStateNode(self, position):
        for key in self.mapping_position_stateNode:
            try:
                if int(str(simplify(to_symbolic(key-position)))) == 0:
                    return self.mapping_position_stateNode[key]
            except:
                pass
        return None

    def addCallReturnNode(self, pc, node):
        if pc in self.mapping_pc_callReturnNode:
            self.mapping_pc_callReturnNode[pc].append(node)
        else:
            self.mapping_pc_callReturnNode[pc] = [node]

    def getCallReturnNode(self, pc):
        return self.mapping_pc_callReturnNode[pc][-1]  # return the most rencent CallReturnNode

    def addExprNode(self, expr, node):
        self.mapping_expr_node[expr] = node

    def getExprNode(self, expr):
        for key in self.mapping_expr_node:
            try:
                if int(str(simplify(key-expr))) == 0:
                    return self.mapping_expr_node[key]
            except Exception:
                pass
        return None

    def addAddressNode(self, expr, node):
        self.mapping_address_node[expr] = node

    def getAddressNode(self, expr):
        for key in self.mapping_address_node:
            try:
                if int(str(simplify(key-expr))) == 0:
                    return self.mapping_address_node[key]
            except:
                pass
        return None


    def getVarNode(self, var):
        if (type(var) == six.integer_types):
            if var in self.mapping_var_node:
                return self.mapping_var_node[var]
            else:
                node = ConstNode(str(var), var)
                self.mapping_var_node[var] = node
                return node
        else:
            var = convertResult(var)
            if var in self.mapping_var_node:
                return self.mapping_var_node[var]
            else:
                raise Exception("no match node for a symbolic var: %s", str(var))

    def addVarNode(self, var, node):
        self.mapping_var_node[var] = node
        self.addNode(node)

    def ssgAddNode(self, node, pid):
        if str(node) in self.ssg.nodes:
            print("here")
        self.ssg.add_node(str(node))
        stored_value = node.arguments[0]
        stored_address = node.arguments[1]
        e_node = ExpressionNode(str(stored_value), stored_value)
        if is_expr(stored_value):
            for x in get_vars(stored_value):
                n = self.getVarNode(x)
                self.ssg.add_edge(n, e_node, label="flowEdge")
        self.ssg.add_edge(e_node, node, label="flowEdge_value")
        a_node = ExpressionNode(str(stored_address), stored_address)
        if is_expr(stored_address):
            for x in get_vars(stored_address):
                n = self.getVarNode(x)
                self.ssg.add_edge(n, a_node, label="flowEdge")
        self.ssg.add_edge(a_node, node, label="flowEdge_address")

        constrains = node.constraint
        c_node = ConstrainNode("constraint", constrains)
        self.ssg.add_edge(c_node, node, label="constraint")


    # The function for construct the graph for the contract
    def addNode(self, node):
        self.count += 1
        self.graph.add_node(node, count=self.count)
        if type(node) == MessageCallNode:
            self.message_call_nodes.append(node)
            if node.name == "CALL":
                self.call_nodes.append(node)
        elif type(node) == StateOPNode:
            self.state_op_nodes.append(node)
            if node.name == "SSTORE":
                self.sstore_nodes.append(node)
        elif type(node) == InputDataNode:
            self.input_data_nodes.append(node)
        elif type(node) == StateNode:
            self.state_nodes.append(node)
        elif type(node) == ArithNode:
            self.arith_nodes.append(node)
        elif type(node) == TerminalNode:
            self.terminal_nodes.append(node)
        elif type(node) == AddressNode:
            self.address_nodes.append(node)
        elif type(node) == SenderNode:
            self.sender_node = node
        elif type(node) == ReceiverNode:
            self.receiver_node = node
        elif type(node) == ReturnStatusNode:
            self.return_status_nodes.append(node)
        elif type(node) == DepositValueNode:
            self.deposit_value_node = node

    def addEdges(self, edgeList, edgeType, branch):
        branchList = [branch]
        self.graph.add_edges_from(edgeList, label=edgeType, branchList=branchList)

    def addEdgeList(self, fromList, toNode, edgeType):
        for fromNode in fromList:
            itemEdge = [(fromNode, toNode)]
            self.graph.add_edges_from(itemEdge, label=edgeType)

    def addBranchEdge(self, edgeList, edgeType, branch):
        for edge in edgeList:
            if self.graph.has_edge(edge[0], edge[1]) and self.graph[edge[0]][edge[1]]["label"] == edgeType:
                self.graph[edge[0]][edge[1]]["branchList"].append(branch)
            else:
                if edgeType == "controlEdge":
                    return
                self.graph.add_edge(edge[0], edge[1], label=edgeType, branchList=[branch])
