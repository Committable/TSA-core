import networkx as nx
from z3 import is_expr, is_const, simplify
from z3.z3util import get_vars

from utils import to_symbolic


class Node:
    count = 0
    
    def __init__(self, name, from_nodes=None, to_nodes=None, lines=None):
        self.count = Node.count
        self.name = name
        self.fromNodes = from_nodes
        self.toNodes = to_nodes
        if lines is None:
            self.lines = XGraph.current_lines
        else:
            self.lines = lines
        Node.count += 1

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
        self.pc = global_pc
        if XGraph.sourcemap is not None and len(XGraph.sourcemap.get_lines_from_pc(self.pc)) == 1:
            self.lines = XGraph.sourcemap.get_lines_from_pc(self.pc)

    def get_pc(self):
        return self.pc

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
        node = graph.add_expression_node(parameter)
        graph.add_branch_edge([(node, self)], "value_flow", path_id, index)
        self.arguments[index].append(node)
        return node

    def __str__(self):
        return ("InstructionNode_" + self.name + "_" + str(self.pc)).replace("\n", "")


class MessageCallNode(InstructionNode):
    def __init__(self, instruction_name, arguments, global_pc):
        super().__init__(instruction_name, arguments, global_pc)

    def __str__(self):
        return ("MessageCallNode_" + self.name + "_" + str(self.pc)).replace("\n", "")


class SStoreNode(InstructionNode):
    def __init__(self, instruction_name, global_pc, arguments):
        super().__init__(instruction_name, arguments, global_pc)

    def __str__(self):
        return (self.name + "_" + str(self.pc)).replace("\n", "")


class TerminalNode(InstructionNode):
    def __init__(self, instruction_name, global_pc):
        super().__init__(instruction_name, [], global_pc)

    def __str__(self):
        return self.name


class ArithNode(InstructionNode):
    def __init__(self, operation, operands, global_pc):
        super().__init__(operation, operands, global_pc)

    def __str__(self):
        return ("ArithNode_" + self.name + "_" + str(self.pc)).replace("\n", "")


class VariableNode(Node):
    def __init__(self, name, value):
        super().__init__(name)
        self.value = value

    def get_value(self):
        return self.value

    def __str__(self):
        return ("VariableNode_" + str(self.count)).replace("\n", "")


class ConstNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("ConstNode_" + str(self.count)).replace("\n", "")


class ExpressionNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("EXPR_" + str(self.count)).replace("\n", "")


class ConstraintNode(VariableNode):
    def __init__(self, pc, name, value, flag=True, parent=None, true_child=None, false_child=None):
        super().__init__(name, value)
        self.parent = None
        self.true_child = None
        self.false_child = None
        self.pc = pc
        self.flag = flag
        if XGraph.sourcemap is not None and len(XGraph.sourcemap.get_lines_from_pc(self.pc)) == 1:
            self.lines = XGraph.sourcemap.get_lines_from_pc(self.pc)

    def set_parent(self, parent):
        self.parent = parent

    def get_parent(self):
        return self.parent

    def set_true_child(self, child):
        self.true_child = child

    def set_false_child(self, child):
        self.false_child = child

    def __str__(self):
        if XGraph.sourcemap is None or len(XGraph.sourcemap.get_lines_from_pc(self.pc)) != 1:
            if self.name:
                return (str(self.name)).replace("\n", "")
            if self.flag:
                return ("*BRANCH_" + str(self.pc)).replace("\n", "")
            else:
                return ("BRANCH_" + str(self.pc)).replace("\n", "")
        else:
            #return XGraph.sourcemap.source.get_content_from_line(XGraph.sourcemap.get_lines_from_pc(self.pc)[0])
            if self.flag:
                return "*" + XGraph.sourcemap.get_contents_from_pc(self.pc).replace("\n", "")
            else:
                return XGraph.sourcemap.get_contents_from_pc(self.pc).replace("\n", "")


class StateNode(VariableNode):
    def __init__(self, name, value, position, pc):
        super().__init__(name, value)
        self.position = position
        self.pc = pc
        if XGraph.sourcemap is not None and len(XGraph.sourcemap.get_lines_from_pc(self.pc)) == 1:
            self.lines = XGraph.sourcemap.get_lines_from_pc(self.pc)

    def __str__(self):
        if len(XGraph.sourcemap.get_lines_from_pc(self.pc)) == 1:
            return ("STATE_" + XGraph.sourcemap.get_contents_from_pc(self.pc)).replace("\n", "")
        else:
            return ("STATE_" + str(self.pc)).replace("\n", "")


class InputDataNode(VariableNode):
    def __init__(self, name, value, start, end):  # include start, exclude end
        super().__init__(name, value)
        self.start = start
        self.end = end

    def __str__(self):
        if is_expr(self.start) or is_expr(self.end):
            return "Input_" + str(self.count)
        else:
            return "Input_" + str(self.start) + "_" + str(self.end)


class InputDataSizeNode(VariableNode):

    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("InputDataSizeNode_" + str(self.count)).replace("\n", "")


class ExpNode(VariableNode):
    def __init__(self, name, value, base, exponent):
        super().__init__(name, value)
        self.base = base
        self.exponent = exponent

    def get_base(self):
        return self.base

    def get_exponent(self):
        return self.exponent

    def __str__(self):
        return ("ExpNode_" + str(self.count)).replace("\n", "")


class GasPriceNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("GasPriceNode_" + str(self.count)).replace("\n", "")


class OriginNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("OriginNode_" + str(self.count)).replace("\n", "")


class CoinbaseNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("CoinbaseNode_" + str(self.count)).replace("\n", "")


class DifficultyNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("DifficultyNode_" + str(self.count)).replace("\n", "")


class GasLimitNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("GasLimitNode_" + str(self.count)).replace("\n", "")


class BlockNumberNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("BlockNumberNode_" + str(self.count)).replace("\n", "")


class TimeStampNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("TimeStampNode_" + str(self.count)).replace("\n", "")


class AddressNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("AddressNode_" + str(self.count)).replace("\n", "")


class BlockhashNode(VariableNode):
    def __init__(self, name, value, block_number):
        super().__init__(name, value)
        self.blockNumber = block_number

    def get_block_number(self):
        return self.blockNumber

    def __str__(self):
        return ("BlockhashNode_" + str(self.count)).replace("\n", "")


class GasNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("GasNode_" + str(self.count)).replace("\n", "")


class ShaNode(VariableNode):
    def __init__(self, name, value, pc, param=None):
        super().__init__(name, value)
        self.param = param
        self.pc = pc

    # param may be None
    def get_param(self):
        return self.param

    def __str__(self):
        if len(XGraph.sourcemap.get_lines_from_pc(self.pc)) == 1:
            self.lines = XGraph.sourcemap.get_lines_from_pc(self.pc)
            return ("SHA_" + XGraph.sourcemap.get_contents_from_pc(self.pc)).replace("\n", "")
        else:
            return ("SHA_"+str(self.pc)).replace("\n", "")


class MemoryNode(VariableNode):  # 32 bytes
    def __init__(self, name, value, position):
        super().__init__(name, value)
        self.position = position

    def get_position(self):
        return self.position

    def __str__(self):
        return ("MemoryNode_" + str(self.count)).replace("\n", "")


class ExtcodeSizeNode(VariableNode):
    def __init__(self, name, value, address):
        super().__init__(name, value)
        self.address = address

    def get_address(self):
        return self.address

    def __str__(self):
        return ("ExtcodeSizeNode_" + str(self.count)).replace("\n", "")


class ExtcodeHashNode(VariableNode):
    def __init__(self, name, value, address):
        super().__init__(name, value)
        self.address = address

    def get_address(self):
        return self.address

    def __str__(self):
        return ("ExtcodeHashNode_" + str(self.count)).replace("\n", "")


class DepositValueNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("DepositValueNode_").replace("\n", "")


class BalanceNode(VariableNode):
    def __init__(self, name, value, address):
        super().__init__(name, value)
        self.address = address

    def get_address(self):
        return self.address

    def __str__(self):
        return ("BalanceNode_" + str(self.count)).replace("\n", "")


class ReturnDataNode(VariableNode):

    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("ReturnDataNode_" + str(self.count)).replace("\n", "")


class ReturnStatusNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("ReturnStatusNode_" + str(self.count)).replace("\n", "")


class ReturnDataSizeNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("ReturnDataSizeNode_" + str(self.count)).replace("\n", "")


class CodeNode(VariableNode):

    def __init__(self, name, value, address):
        super().__init__(name, value)
        self.address = address

    def __str__(self):
        return ("CodeNode_" + str(self.count)).replace("\n", "")


class SenderNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return "msg.sender"


class ReceiverNode(VariableNode):
    def __init__(self, name, value):
        super().__init__(name, value)

    def __str__(self):
        return ("ReceiverNode_" + str(self.count)).replace("\n", "")


class XGraph:
    sourcemap = None
    current_lines = []

    def __init__(self, cname="", sourcemap=None):
        if sourcemap is not None:
            XGraph.sourcemap = sourcemap
        self.graph = nx.DiGraph(name=cname)

        self.count = 0
        self.constraint_count = 0

        self.overflow_related = ('ADD', 'SUB', 'MUL', 'EXP')

        # nodes in graph
        self.arith_nodes = []  # only for {"add", "sub", "mul", "exp"}
        self.sload_nodes = []  # all nodes included in {sstore, sload}
        self.sstore_nodes = []  # for sstore instruction
        self.input_data_nodes = set()  # for {calldataload, calldatacopy}
        self.terminal_nodes = []  # for "revert"
        self.sender_node = None  # for msg.sender
        self.receiver_node = None  # for receiver
        self.deposit_value_node = None  # Iv
        self.origin_node = None  # for "origin"
        self.coin_base_node = None
        self.difficulty_node = None
        self.gas_limit_node = None
        self.time_stamp_node = None
        self.block_number_nodes = set()
        self.address_nodes = []  # for all address nodes
        self.exp_nodes = set()
        self.sha_nodes = set()
        self.blockhash_nodes = set()
        self.return_status_nodes = []  # for all return status nodes
        # (expr, ExpressionNode)
        self.mapping_expr_node = {}
        # (constrain, ConstrainNode)
        self.mapping_constraint_node = {}
        # (expr/var, AddressNode)
        self.mapping_address_node = {}
        # (pc, MessageCallNode)
        self.mapping_pc_message_call_node = {}
        # (pc, StateOpNode)
        self.mapping_pc_state_op_node = {}
        # (pc, TerminalNode(
        self.mapping_pc_terminal_node = {}
        # (position, StateNode)
        self.mapping_position_state_node = {}
        # (address, BalanceNode)
        self.mapping_address_balance_node = {}
        # constraint tree root
        self.constraint_root = None

        # nodes may not in graph, but cached
        # (Var, VariableNode), mapping symbolic variable or real int to variableNodes or constNodes
        self.mapping_var_node = {}

        # current constraint node
        self.current_constraint_node = None



    def reset_graph(self, function_name):
        self.graph = nx.DiGraph(name=function_name)

    def get_graph(self):
        return self.graph

    def add_expression_node(self, expr):  # is_expr(expr) == True and is_const(expr)==False
        if not is_expr(expr):
            return self.get_var_node(expr)
        if is_expr(expr) and is_const(expr):
            return self.get_var_node(expr)
        e_node = self.get_expr_node(expr)
        if e_node is None:
            e_node = ExpressionNode(str(expr), expr)
            self.graph.add_node(e_node)
            self.mapping_expr_node[expr] = e_node
            flow_edges = []
            for var in get_vars(expr):
                node = self.get_var_node(var)
                flow_edges.append((node, e_node))
            self.add_branch_edge(flow_edges, "value_flow")
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

    def add_constraint_node(self, constraint, pc=0, name=None, flag=True):
        if name is None:
            name = ""
        assert(is_expr(constraint))

        e_node = self.get_constraint_node(pc)
        if e_node is None:
            e_node = ConstraintNode(pc, name, constraint, flag)
            e_node.set_parent(self.current_constraint_node)
            self.graph.add_node(e_node)
            self.mapping_constraint_node[pc] = e_node
        flow_edges = []
        # if not is_const(constraint):
        #     for var in get_vars(constraint):
        #         node = self.get_var_node(var)
        #         flow_edges.append((node, e_node))
        # self.add_branch_edge(flow_edges, "value_flow", None)

        if self.constraint_root is None:
            self.constraint_root = e_node
        if self.current_constraint_node is not None:
            if flag:
                self.current_constraint_node.set_true_child(e_node)
            else:
                self.current_constraint_node.set_false_child(e_node)
            self.add_branch_edge([(self.current_constraint_node, e_node)], "control_flow", bool_flag=flag)
        self.current_constraint_node = e_node
        return e_node

    def get_constraint_node(self, pc):
        if pc in self.mapping_constraint_node:
            return self.mapping_constraint_node[pc]
        else:
            return None

    def out_constraint(self):
        self.current_constraint_node = self.current_constraint_node.get_parent()

    def get_current_constraint_node(self):
        return self.current_constraint_node

    def add_state_node(self, position, node):
        tmp = self.get_state_node(position)
        if tmp is not None:
            return tmp
        else:
            self.mapping_position_state_node[position] = node
            self.add_var_node(node.get_value(), node)
            p_node = self.add_expression_node(position)
            self.add_branch_edge([(p_node, node)], "value_flow")
            return node

    def get_state_node(self, position):
        for key in self.mapping_position_state_node:
            try:
                if int(str(simplify(to_symbolic(key - position)))) == 0:
                    return self.mapping_position_state_node[key]
            except:
                pass
        return None

    def add_message_call_node(self, name, pc, parameters, return_node, path_id):
        if pc in self.mapping_pc_message_call_node:
            node = self.mapping_pc_message_call_node[pc]
        else:
            if name in ("DELEGATECALL", "STATICCALL"):
                node = MessageCallNode(name, [[], [], [], [], [], []], pc)
            else:
                node = MessageCallNode(name, [[], [], [], [], [], [], []], pc)
            self.mapping_pc_message_call_node[pc] = node
        for i in range(0, len(parameters)):
            node.add_arguments(self, parameters[i], i, path_id)

        self.add_var_node(return_node.get_value(), return_node)
        self.add_branch_edge([(node, return_node)], "value_flow", path_id)

        return node

    def add_terminal_node(self, node):
        if node.get_pc() in self.mapping_pc_terminal_node:
            node = self.mapping_pc_terminal_node[node.get_pc()]
        else:
            self.mapping_pc_terminal_node[node.get_pc()] = node
        self.add_branch_edge([(self.current_constraint_node, node)], "constraint_flow")

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
        if var in self.mapping_var_node:
            self._add_node(self.mapping_var_node[var])
            return self.mapping_var_node[var]
        else:
            if is_expr(var):
                node = VariableNode(str(var), var)
            else:
                node = ConstNode(str(var), var)
            return self.add_var_node(var, node)

    def add_var_node(self, var, node):
        node = self.cache_var_node(var, node)
        self._add_node(node)
        return node

    def cache_var_node(self, var, node):
        if var in self.mapping_var_node:
            return self.mapping_var_node[var]
        self.mapping_var_node[var] = node
        return node

    def add_sstore_node(self, node: SStoreNode, parameters, path_id):
        if node.get_pc() in self.mapping_pc_state_op_node:
            node = self.mapping_pc_state_op_node[node.get_pc()]
        for i in range(0, len(parameters)):
            node.add_arguments(self, parameters[i], i, path_id)
        self.add_branch_edge([(self.current_constraint_node, node)], "constraint_flow", path_id, True)
        return node

    def change_balance_node(self, address, init_value, new_balance, path_id):
        init_node = None
        for key in self.mapping_address_balance_node:
            try:
                if int(str(simplify(to_symbolic(key - address)))) == 0:
                    init_node = self.mapping_address_balance_node[key]
            except:
                pass
        if init_node is None:
            init_node = BalanceNode("init_"+str(address), init_value, address)
            init_node = self.add_var_node(init_value, init_node)
        balance_expression = self.add_expression_node(new_balance)
        self.add_branch_edge([(balance_expression, init_node)], "value_flow", path_id, True)
        self.add_branch_edge([(self.current_constraint_node, init_node)], "constraint_flow", path_id, True)

    def add_branch_edge(self, edge_list, edge_type, branch=None, bool_flag=True):
        for edge in edge_list:
            if self.graph.has_edge(edge[0], edge[1]) and self.graph[edge[0]][edge[1]]["label"] == edge_type:
                if branch:
                    self.graph[edge[0]][edge[1]]["branchList"].append(branch)
            else:
                if branch:
                    self.graph.add_edge(edge[0], edge[1], label=edge_type, branchList=[branch], boolFlag=bool_flag)
                else:
                    self.graph.add_edge(edge[0], edge[1], label=edge_type, branchList=[], boolFlag=bool_flag)

    # The function for construct the graph for the contract
    def _add_node(self, node):
        # TODO: count is useless, it can be deleted
        if node in self.graph.nodes:
            return
        self.count += 1
        self.graph.add_node(node, count=self.count)

        if type(node) == InputDataNode:  # Todo: add start and end node to input_data_node
            self.input_data_nodes.add(node)
        elif type(node) == ArithNode:
            self.arith_nodes.append(node)
        elif type(node) == TerminalNode:
            self.terminal_nodes.append(node)
        elif type(node) == AddressNode:
            self.address_nodes.append(node)
        elif type(node) == SenderNode:  #
            self.sender_node = node
        elif type(node) == ReceiverNode:  #
            self.receiver_node = node
        elif type(node) == ReturnStatusNode:
            self.return_status_nodes.append(node)
        elif type(node) == DepositValueNode:  #
            self.deposit_value_node = node
        elif type(node) == BalanceNode:
            # add value_flow from address_node to balance_node
            address_node = self.add_address_node(node.get_address())
            self.add_branch_edge([(address_node, node)], "value_flow")
            self.mapping_address_balance_node[node.get_address()] = node
        elif type(node) == OriginNode:  #
            self.origin_node = node
        elif type(node) == CoinbaseNode:  #
            self.coin_base_node = node
        elif type(node) == BlockNumberNode:  #
            self.block_number_nodes.add(node)
        elif type(node) == DifficultyNode:  #
            self.difficulty_node = node
        elif type(node) == GasLimitNode:  #
            self.gas_limit_node = node
        elif type(node) == TimeStampNode:
            self.time_stamp_node = node
        elif type(node) == ExpNode:
            # add value from base_node and exponent_node to exp_node
            base_expr_node = self.add_expression_node(node.get_base())
            self.add_branch_edge([(base_expr_node, node)], "value_flow")
            exponent_expr_node = self.add_expression_node(node.get_exponent())
            self.add_branch_edge([(exponent_expr_node, node)], "value_flow")
            self.exp_nodes.add(node)
        elif type(node) == ShaNode:
            # add value from var_node in param to sha_node
            param = node.get_param()
            if param is not None:
                if not is_const(param):
                    for var in get_vars(param):
                        var_node = self.get_var_node(var)
                        self.add_branch_edge([(var_node, node)], "value_flow")
                else:
                    var_node = self.get_var_node(param)
                    self.add_branch_edge([(var_node, node)], "value_flow")
            self.sha_nodes.add(node)
        elif type(node) == ExtcodeSizeNode:
            # add value_flow from address_node to ext_code_size_node
            address_node = self.add_address_node(node.get_address())
            self.add_branch_edge([(address_node, node)], "value_flow")
        elif type(node) == BlockhashNode:
            block_number_node = self.add_expression_node(node.get_block_number())
            self.add_branch_edge([(block_number_node, node)], "value_flow")
            self.blockhash_nodes.add(node)
        elif type(node) == MemoryNode:
            position_node = self.add_expression_node(node.get_position())
            self.add_branch_edge([(position_node, node)], "value_flow")





