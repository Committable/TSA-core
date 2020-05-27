import networkx as nx
import re
import six
from z3 import *
from solver.symbolicVar import *
import global_params
from utils import isReal


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

class ExpressionNode(Node):
    def __init__(self, name, expression):
        super().__init__(name)
        self.expression = expression

    def get_expression(self):
        return self.expression

    def set_expression(self, expression):
        self.expression = expression

class InstructionNode(Node):

    def __init__(self, instruction_name, arguments, global_pc, constraint):
        super().__init__()
        self.name = instruction_name
        self.arguments = arguments
        self.global_pc = global_pc
        self.constraint = constraint

    def getConstraints(self):
        return self.constraint

    def getArguments(self):
        return self.arguments


class MessageCallNode(InstructionNode):

    def __init__(self, instruction_name, arguments, global_pc, constraint):
        super().__init__(instruction_name, arguments, global_pc, constraint)

    def __str__(self):
        return self.name + "_" + str(self.global_pc)


class StateOPNode(InstructionNode):

    def __init__(self, instruction_name, arguments, global_pc, constraint, nodeID):
        super().__init__(instruction_name, arguments, global_pc, constraint, nodeID)

    def __str__(self):
        return "StateOPNode " + self.name + " " + str(self.nodeID)


class VariableNode(Node):

    def __init__(self, name, value):
        super().__init__(name)
        self.value = value


class StateNode(VariableNode):

    def __init__(self, name, value, position):
        super().__init__(name, value)
        self.position = position

    def __str__(self):
        return "StateNode " + str(self.name) + " " + str(self.nodeID)


class ConstNode(VariableNode):

    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return self.name


class InputDataNode(VariableNode):

    def __init__(self, name, value, position):
        super().__init__(name, value)
        self.position = position

    def __str__(self):
        return self.name


class InputDataSizeNode(VariableNode):

    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return self.name

class ExpNode(VariableNode):

    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return self.name

class GasPriceNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return self.name

class OriginNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return self.name

class CoinbaseNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return self.name

class DifficultyNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return self.name

class GasLimitNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return self.name

class CurrentNumberNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return self.name

class TimeStampNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return self.name

class AddressNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return self.name

class BlockhashNode(VariableNode):
    def __init__(self, name, value, blockNumber):
        super().__init__(name, value)
        self.blockNumber = blockNumber

    def __str__(self):
        return self.name

class GasNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return self.name

class ShaNode(VariableNode):

    def __init__(self, name, value, args):
        super().__init__(name, value)
        self.args = args

    def __str__(self):
        return self.name

class MemoryNode(VariableNode):

    def __init__(self, name, value, position):
        super().__init__(name, value)
        self.position = position

    def __str__(self):
        return self.name

class ExtcodeSizeNode(VariableNode):
    def __init__(self, name, value, address):
        super().__init__(name, value)
        self.address = address

    def __str__(self):
        return self.name

class DepositValueNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return self.name

class BalanceNode(VariableNode):
    def __init__(self, name, value, address):
        super().__init__(name, value)
        self.address = address

    def __str__(self):
        return self.name

class ReturnDataNode(VariableNode):

    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return self.name

class ReturnStatusNode(VariableNode):

    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return self.name

class ReturnDataSizeNode(VariableNode):

    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return self.name

class CodeNode(VariableNode):

    def __init__(self, name, value, address):
        super().__init__(name, value)
        self.address = address

    def __str__(self):
        return self.name


class TerminalNode(InstructionNode):

    def __init__(self, instruction_name, arguments, global_pc, constraint):
        super().__init__(instruction_name, arguments, global_pc, constraint)

    def __str__(self):
        return "TerminalNode " + self.name

class ArithNode(InstructionNode):

    def __init__(self, operation, operand, global_pc, constraint, expression, param):
        super().__init__(operation, operand, global_pc, constraint)
        self.expression = expression
        self.params = param

    def __str__(self):
        return "ArithNode " + self.name

class FlowEdge:

    def __init__(self, expression):
        self.expression = expression

    def getExpression(self):
        return self.expression


class ControlEdge:

    def __init__(self, constraints):
        self.constraints = constraints

    def getConstraint(self):
        return self.constraints


class XGraph:

    def __init__(self):
        self.graph = nx.DiGraph()
        self.count = 0
        self.overflow_related = ('ADD', 'SUB', 'MUL', 'EXP')
        self.instruction_nodes = []  # TODO: add comment
        self.message_call_nodes = []  # all nodes included in {call, staticcall, delegatecall, callcode}
        self.msg_data_nodes = []  # TODO: add comment
        self.arith_nodes = set()  # only for {"add", "sub", "mul", "exp"}
        self.input_data_nodes = []  # for {calldataload, calldatacopy}
        self.block_data_nodes = []  # for {blockhash}
        self.state_op_nodes = []  # all nodes included in {sstore, sload}
        self.call_nodes = []  # for call instruction
        self.msg_sender_nodes = []
        self.state_nodes = []
        self.sstore_nodes = []  # for sstore instruction
        self.sender_node = ""  # for msg.sender

        # (Var, VariableNode), mapping symbolic or real int to variableNodes
        self.mapping_var_node = {}
        # (expr, ExpressionNode)
        self.mapping_expr_node = {}
        # (expr/var, AddressNode)
        self.mapping_address_node = {}
        # (pc, [CallReturnNode])
        self.mapping_pc_callReturnNode = {}
        # (position, StateNode)
        self.mapping_position_stateNode = {}

    def addStateNode(self, position, node):
        self.mapping_position_stateNode[position] = node

    def getStateNode(self, position):
        s = SSolver()
        s.set("timeout", global_params.TIMEOUT)
        for key in self.mapping_position_stateNode:
            s.push()
            s.add(Not(key == position))
            if check_unsat(s):
                s.pop()
                return self.mapping_position_stateNode[key]
            s.pop()
        return None

    def addCallReturnNode(self, pc, node):
        if pc in self.mapping_pc_callReturnNode:
            self.mapping_pc_callReturnNode[pc].append(node)
        else:
            self.mapping_pc_callReturnNode[pc] = [node]

    def getCallReturnNode(self, pc):
        return self.mapping_pc_callReturnNode[pc][-1]  # return the most rencent CallReturnNode

    def addExprNode(self, expr, node):
        if is_const(expr) or isReal(expr):
            expr = convertResult(expr)
            self.mapping_var_node[expr] = node
        else:
            self.mapping_expr_node[expr] = node

    def getExprNode(self, expr):
        s = SSolver()
        s.set("timeout", global_params.TIMEOUT)
        if is_const(expr) or isReal(expr):  # expr is variable or const
            expr = convertResult(expr)  # all value of const are in real int type
            for key in self.mapping_var_node:
                s.push()
                s.add(Not(key == expr))
                if check_unsat(s):
                    s.pop()
                    return self.mapping_var_node[key]
                s.pop()
        else:
            for key in self.mapping_expr_node:
                s.push()
                s.add(Not(key == expr))
                if check_unsat(s):
                    s.pop()
                    return self.mapping_expr_node[key]
                s.pop()
        return None

    def addAddressNode(self, expr, node):
        self.mapping_address_node[expr] = node

    def getAddressNode(self, expr):
        s = SSolver()
        s.set("timeout", global_params.TIMEOUT)

        for key in self.mapping_address_node:
            s.push()
            s.add(Not(key == expr))
            if check_unsat(s):
                s.pop()
                return self.mapping_address_node[key]
            s.pop()
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
        elif type(node) == BlockDataNode:
            self.block_data_nodes.append(node)
        elif type(node) == MsgDataNode:
            self.msg_data_nodes.append(node)
            if node.name == "CALLER":
                self.msg_sender_nodes.append(node)
        elif type(node) == StateNode:
            if node.source == "Ia":
                self.state_nodes.append(node)
            elif node.source == "Is":
                self.sender_node = node
        elif type(node) == ArithNode:
            self.arith_nodes.append(node)

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
                self.graph.add_edge(edge[0], edge[1], label=edgeType, branchList=[branch])
