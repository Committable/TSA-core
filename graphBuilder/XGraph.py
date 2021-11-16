import networkx as nx
from z3 import is_expr, is_const, simplify
from z3.z3util import get_vars

from utils import to_symbolic


class Node:
    def __init__(self, name, from_nodes=None, to_nodes=None):
        self.name = name
        self.fromNodes = from_nodes
        self.toNodes = to_nodes

    def get_from_nodes(self, graph):
        if self.fromNodes is None:
            self.fromNodes = list(graph.perdecessors(self))
        return self.fromNodes

    def get_to_nodes(self, graph):
        if self.toNodes is None:
            self.toNodes = list(graph.successors(self))
        return self.toNodes

    def __str__(self):
        return ("Node_" + self.name).replace("\n", "")


class InstructionNode(Node):
    def __init__(self, instruction_name, arguments, global_pc):
        super().__init__(instruction_name)
        self.arguments = arguments  # arguments: [[node1,node1], [node2,node3]]
        self.global_pc = global_pc

    def get_arguments(self):
        return self.arguments

    def add_arguments(self, graph, parameter, index, path_id):
        for x in self.arguments[index]:
            properties = graph.graph.edges[(x, self)]
            try:
                # TODO: is this better than Solver.solver(parameter-x == 0)?
                if int(str(simplify(to_symbolic(parameter - x.get_value())))) == 0:
                    properties["branchList"].append(path_id)
                    self.arguments[index].append(x)
                    return x
            except:
                pass
        node = graph.add_expression_node(parameter, path_id)
        graph.add_branch_edge([(node, self)], "value_flow", path_id, index)
        self.arguments[index].append(node)
        return node

    def __str__(self):
        return ("InstructionNode_" + self.name + "_" + str(self.global_pc)).replace("\n", "")


class MessageCallNode(InstructionNode):
    def __init__(self, instruction_name, arguments, global_pc):
        super().__init__(instruction_name, arguments, global_pc)

    def __str__(self):
        return ("MessageCallNode_" + self.name + "_" + str(self.global_pc)).replace("\n", "")


class StateOPNode(InstructionNode):
    def __init__(self, instruction_name, arguments, global_pc):
        super().__init__(instruction_name, arguments, global_pc)

    def __str__(self):
        return ("StateOPNode_" + self.name + "_" + str(self.global_pc)).replace("\n", "")


class TerminalNode(InstructionNode):
    def __init__(self, instruction_name, global_pc):
        super().__init__(instruction_name, [], global_pc)

    def __str__(self):
        return ("TerminalNode_" + self.name + "_" + str(self.global_pc)).replace("\n", "")


class ArithNode(InstructionNode):
    def __init__(self, operation, operands, global_pc):
        super().__init__(operation, operands, global_pc)

    def __str__(self):
        return ("ArithNode_" + self.name + "_" + str(self.global_pc)).replace("\n", "")


class VariableNode(Node):
    def __init__(self, name, value):
        super().__init__(name)
        self.value = value

    def get_value(self):
        return self.value

    def __str__(self):
        return ("VariableNode_" + self.name + "_" + str(self.value)).replace("\n", "")


class ConstNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("ConstNode_" + self.name).replace("\n", "")


class ExpressionNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("ExpressionNode_" + self.name).replace("\n", "")


class ConstrainNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("ConstrainNode_" + self.name).replace("\n", "")


class StateNode(VariableNode):
    def __init__(self, name, value, position):
        super().__init__(name, value)
        self.position = position

    def __str__(self):
        return ("StateNode_" + str(self.name) + "_" + str(self.position)).replace("\n", "")


class InputDataNode(VariableNode):

    def __init__(self, name, value, position):
        super().__init__(name, value)
        self.position = position

    def __str__(self):
        return ("InputDataNode_" + self.name).replace("\n", "")


class InputDataSizeNode(VariableNode):

    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("InputDataSizeNode_" + self.name).replace("\n", "")


class ExpNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("ExpNode_" + self.name).replace("\n", "")


class GasPriceNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("GasPriceNode_" + self.name).replace("\n", "")


class OriginNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("OriginNode_" + self.name).replace("\n", "")


class CoinbaseNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("CoinbaseNode_" + self.name).replace("\n", "")


class DifficultyNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("DifficultyNode_" + self.name).replace("\n", "")


class GasLimitNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("GasLimitNode_" + self.name).replace("\n", "")


class CurrentNumberNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("CurrentNumberNode_" + self.name).replace("\n", "")


class TimeStampNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("TimeStampNode_" + self.name).replace("\n", "")


class AddressNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("AddressNode_" + self.name).replace("\n", "")


class BlockhashNode(VariableNode):
    def __init__(self, name, value, block_number):
        super().__init__(name, value)
        self.blockNumber = block_number

    def __str__(self):
        return ("BlockhashNode_" + self.name + "_" + str(self.blockNumber)).replace("\n", "")


class GasNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("GasNode_" + self.name).replace("\n", "")


class ShaNode(VariableNode):
    def __init__(self, name, value, args):
        super().__init__(name, value)
        self.args = args

    def __str__(self):
        return ("ShaNode_" + str(self.args)).replace("\n", "")


class MemoryNode(VariableNode):
    def __init__(self, name, value, position):
        super().__init__(name, value)
        self.position = position

    def __str__(self):
        return ("MemoryNode_" + self.name).replace("\n", "")


class ExtcodeSizeNode(VariableNode):
    def __init__(self, name, value, address):
        super().__init__(name, value)
        self.address = address

    def __str__(self):
        return ("ExtcodeSizeNode_" + self.name).replace("\n", "")


class DepositValueNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("DepositValueNode_" + self.name).replace("\n", "")


class BalanceNode(VariableNode):
    def __init__(self, name, value, address):
        super().__init__(name, value)
        self.address = address

    def __str__(self):
        return ("BalanceNode_" + self.name).replace("\n", "")


class ReturnDataNode(VariableNode):

    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("ReturnDataNode_" + self.name).replace("\n", "")


class ReturnStatusNode(VariableNode):

    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("ReturnStatusNode_" + self.name).replace("\n", "")


class ReturnDataSizeNode(VariableNode):

    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("ReturnDataSizeNode_" + self.name).replace("\n", "")


class CodeNode(VariableNode):

    def __init__(self, name, value, address):
        super().__init__(name, value)
        self.address = address

    def __str__(self):
        return ("CodeNode_" + self.name).replace("\n", "")


class SenderNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("SenderNode_" + self.name).replace("\n", "")


class ReceiverNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("ReceiverNode_" + self.name).replace("\n", "")


class XGraph:
    def __init__(self, cname=""):
        self.graph = nx.DiGraph(name=cname)

        self.count = 0
        self.constraint_count = 0

        self.overflow_related = ('ADD', 'SUB', 'MUL', 'EXP')

        # nodes in graph
        self.message_call_nodes = []  # all nodes included in {call, staticcall, delegatecall, callcode}
        self.call_nodes = []  # for "call" instruction
        self.arith_nodes = []  # only for {"add", "sub", "mul", "exp"}
        self.sload_nodes = []  # all nodes included in {sstore, sload}
        self.sstore_nodes = []  # for sstore instruction
        self.input_data_nodes = []  # for {calldataload, calldatacopy}
        self.state_nodes = []
        self.terminal_nodes = []  # for "revert"
        self.sender_node = None  # for msg.sender
        self.receiver_node = None  # for receiver
        self.deposit_value_node = None  # Iv
        self.address_nodes = []  # for all address nodes
        self.return_status_nodes = []  # for all return status nodes
        # (expr, ExpressionNode)
        self.mapping_expr_node = {}
        # (constrain, ConstrainNode)
        self.mapping_constrain_node = {}
        # (expr/var, AddressNode)
        self.mapping_address_node = {}
        # (pc, MessageCallNode)
        self.mapping_pc_message_call_node = {}
        # (position, StateNode)
        self.mapping_position_state_node = {}

        # nodes may not in graph, but cached
        # (Var, VariableNode), mapping symbolic variable or real int to variableNodes or constNodes
        self.mapping_var_node = {}

    def add_expression_node(self, expr, path_id):  # is_expr(expr) == True and is_const(expr)==False
        if not is_expr(expr):
            return self.get_var_node(expr)
        if is_expr(expr) and is_const(expr):
            return self.get_var_node(expr)
        e_node = self.get_expr_node(expr)
        if e_node is None:
            e_node = ExpressionNode(str(expr), expr)
            self.mapping_expr_node[expr] = e_node
            flow_edges = []
            for var in get_vars(expr):
                node = self.get_var_node(var)
                flow_edges.append((node, e_node))
            self.add_branch_edge(flow_edges, "value_flow", None)
            return e_node
        else:
            return e_node

    def get_expr_node(self, expr):
        for key in self.mapping_expr_node:
            try:
                if int(str(simplify(to_symbolic(key - expr)))) == 0:
                    return self.mapping_expr_node[key]
            except:
                pass
        return None

    def add_constrain_node(self, constraint):
        assert(is_expr(constraint))
        self.constraint_count += 1
        e_node = ConstrainNode(str(constraint), constraint)
        self.mapping_address_node[str(constraint) + "_" + str(self.constraint_count)] = e_node
        flow_edges = []
        if is_const(constraint):
            return e_node
        else:
            for var in get_vars(constraint):
                node = self.get_var_node(var)
                flow_edges.append((node, e_node))
        self.add_branch_edge(flow_edges, "value_flow", None)
        return e_node

    def add_state_node(self, position, node):
        tmp = self.get_state_node(position)
        if tmp is not None:
            return tmp
        else:
            self.mapping_position_state_node[position] = node
            return node

    def get_state_node(self, position):
        for key in self.mapping_position_state_node:
            try:
                if int(str(simplify(to_symbolic(key - position)))) == 0:
                    return self.mapping_position_state_node[key]
            except:
                pass
        return None

    def add_message_call_node(self, pc, node):
        if pc in self.mapping_pc_message_call_node:
            return self.mapping_pc_message_call_node[pc]
        else:
            self.mapping_pc_message_call_node[pc] = node
            return node

    def get_call_return_node(self, pc):
        if pc in self.mapping_pc_message_call_node:
            return self.mapping_pc_message_call_node[pc]
        return None

    def add_address_node(self, expr):
        a_node = self.get_address_node(expr)
        if a_node is None:
            a_node = AddressNode(str(expr), expr)
            self.mapping_address_node[expr] = a_node
            self.graph.add_node(a_node)
            flow_edges = []
            if not is_expr(expr):
                flow_edges.append((self.get_var_node(expr), a_node))
            else:
                for var in get_vars(expr):
                    node = self.get_var_node(var)
                    flow_edges.append((node, a_node))
            self.add_branch_edge(flow_edges, "value_flow", None)
            return a_node
        else:
            return a_node

    def get_address_node(self, expr):
        for key in self.mapping_address_node:
            try:
                if int(str(simplify(to_symbolic(key - expr)))) == 0:
                    return self.mapping_address_node[key]
            except:
                pass
        return None

    def get_var_node(self, var):
        if var in self.graph:
            return self.mapping_var_node[var]
        else:
            if var in self.mapping_var_node:
                self._add_node(self.mapping_var_node[var])
                return self.mapping_var_node[var]
            else:
                if is_expr(var):
                    node = VariableNode(str(var), var)
                else:
                    node = ConstNode(str(var), var)
                self.add_var_node(var, node)
                return node

    def add_var_node(self, var, node):
        node = self.cache_var_node(var, node)
        self._add_node(node)
        return node

    def cache_var_node(self, var, node):
        if var in self.mapping_var_node:
            return self.mapping_var_node
        self.mapping_var_node[var] = node
        return node

    # TODO: why need branch and branchList?
    def add_branch_edge(self, edge_list, edge_type, branch, idx=None):
        for edge in edge_list:
            if self.graph.has_edge(edge[0], edge[1]) and self.graph[edge[0]][edge[1]]["label"] == edge_type:
                if branch:
                    self.graph[edge[0]][edge[1]]["branchList"].append(branch)
            else:
                if branch:
                    self.graph.add_edge(edge[0], edge[1], label=edge_type, branchList=[branch], idx=idx)
                else:
                    self.graph.add_edge(edge[0], edge[1], label=edge_type, branchList=[], idx=idx)

    # The function for construct the graph for the contract
    def _add_node(self, node):
        # TODO: count is useless, it can be deleted
        self.count += 1
        self.graph.add_node(node, count=self.count)

        if type(node) == MessageCallNode:
            self.message_call_nodes.append(node)
            if node.name == "CALL":
                self.call_nodes.append(node)
        elif type(node) == StateOPNode:
            if node.name == "SLOAD":
                self.sload_nodes.append(node)
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

